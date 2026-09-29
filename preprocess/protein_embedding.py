import argparse
import gzip
import hashlib
import json
import logging
import os
import shutil
import urllib.request
from pathlib import Path

import esm
import h5py
import numpy as np
import torch
from Bio import SeqIO
from esm import FastaBatchedDataset
from esm.data import Alphabet

PREPROCESS_DIR = Path(__file__).resolve().parent
STABLE_ID_DIR = PREPROCESS_DIR / "gene_protein_stable_ids"
FASTA_MANIFEST = PREPROCESS_DIR / "fasta_manifest_pep.json"


def sha256_file(path):
    """Hash a source or cached model without loading it into memory."""
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path, value):
    temporary = path.with_name(path.name + ".tmp")
    with open(temporary, "w", encoding="utf-8") as output:
        json.dump(value, output, sort_keys=True, indent=2)
        output.flush()
        os.fsync(output.fileno())
    os.replace(temporary, path)


def completed_chunk(path, identity, batch_idx, expected_labels):
    """Accept only a fully published chunk belonging to this exact run."""
    try:
        with h5py.File(path, "r") as chunk:
            labels = [value.decode("utf-8") for value in chunk["labels"][:]]
            vectors = chunk["vectors"]
            values = vectors[:]
            digest = hashlib.sha256()
            digest.update(json.dumps(labels, ensure_ascii=False).encode("utf-8"))
            digest.update(values.tobytes())
            return (
                chunk.attrs["identity"] == identity
                and chunk.attrs["batch_idx"] == batch_idx
                and labels == list(expected_labels)
                and vectors.ndim == 2
                and vectors.shape[0] == len(labels)
                and vectors.shape[1] > 0
                and np.isfinite(values).all()
                and chunk.attrs["sha256"] == digest.hexdigest()
            )
    except (OSError, KeyError, UnicodeDecodeError, ValueError):
        return False


def publish_chunk(path, identity, batch_idx, labels, vectors):
    temporary = path.with_name(path.name + ".tmp")
    vectors = np.asarray(vectors, dtype=np.float32)
    if vectors.ndim != 2 or not np.isfinite(vectors).all():
        raise ValueError(f"Nonfinite or malformed protein embeddings for batch {batch_idx}")
    digest = hashlib.sha256()
    digest.update(json.dumps(labels, ensure_ascii=False).encode("utf-8"))
    digest.update(vectors.tobytes())
    with h5py.File(temporary, "w") as chunk:
        chunk.attrs["identity"] = identity
        chunk.attrs["batch_idx"] = batch_idx
        chunk.attrs["sha256"] = digest.hexdigest()
        chunk.create_dataset("labels", data=np.asarray(labels, dtype="S"))
        chunk.create_dataset("vectors", data=vectors)
        chunk.flush()
    os.replace(temporary, path)


def publish_gene_embeddings(save_file, chunks, identity, gene_ids):
    """Average all protein isoforms with bounded RAM; publish only when complete."""
    output = Path(save_file)
    aggregate_path = output.with_name(output.name + ".aggregate.tmp.h5")
    output_tmp = output.with_name(output.name + ".tmp.h5")
    gene_indices = {gene_id: i for i, gene_id in enumerate(gene_ids)}
    with h5py.File(chunks[0], "r") as first_chunk:
        dimension = first_chunk["vectors"].shape[1]

    with h5py.File(aggregate_path, "w") as aggregate:
        sums = aggregate.create_dataset("sums", (len(gene_ids), dimension), dtype="f8", fillvalue=0)
        counts = aggregate.create_dataset("counts", (len(gene_ids),), dtype="i8", fillvalue=0)
        for chunk_path in chunks:
            with h5py.File(chunk_path, "r") as chunk:
                labels = [value.decode("utf-8") for value in chunk["labels"][:]]
                for i, gene_id in enumerate(labels):
                    row = gene_indices[gene_id]
                    sums[row] = sums[row] + chunk["vectors"][i]
                    counts[row] = counts[row] + 1
        with h5py.File(output_tmp, "w") as result:
            result.attrs["identity"] = identity
            result.attrs["complete"] = True
            result.create_dataset("keys", data=np.asarray(gene_ids, dtype="S"))
            arrays = result.create_group("arrays")
            for row, gene_id in enumerate(gene_ids):
                if counts[row] == 0:
                    raise RuntimeError(f"No protein embedding for {gene_id}")
                arrays.create_dataset(gene_id, data=(sums[row] / counts[row]).astype(np.float32))
            result.flush()
    os.replace(output_tmp, output)
    aggregate_path.unlink()


def clean_sequence(seq: str):
    """
    Cleans the input protein sequence by replacing any asterisk (*) characters with the <unk> token.

    Args:
        seq (str): The input protein sequence.

    Returns
    -------
        str: The cleaned protein sequence with asterisks replaced by <unk>.
    """
    return seq.replace("*", "<unk>")


def pad_batch(toks, num_gpus):
    """
    Pads the batch to ensure its size is a multiple of the number of GPUs.

    Args:
        toks (torch.Tensor): The tokenized sequences.
        num_gpus (int): The number of GPUs.

    Returns
    -------
        torch.Tensor: The padded tokenized sequences.
    """
    batch_size = toks.size(0)
    if batch_size % num_gpus != 0:
        padding_size = num_gpus - (batch_size % num_gpus)
        padding = torch.zeros((padding_size, toks.size(1)), dtype=toks.dtype)
        toks = torch.cat([toks, padding], dim=0)
    return toks


def generate_embeddings(
    model: torch.nn.Module,
    alphabet: Alphabet,
    fasta: str,
    save_file: str,
    seq_length=1022,
    max_tokens=2048,
    model_name="esm2_t36_3B_UR50D",
    model_sha256=None,
    source_sha256=None,
    source_url=None,
    layer=33,
):
    """
    Generates embeddings for protein sequences from a given FASTA file using a pre-trained model.

    Args:
        model (torch.nn.Module): The pre-trained PyTorch model to use for generating embeddings.
        alphabet (Alphabet): The alphabet object used for encoding sequences.
        fasta (str): Path to the input FASTA file containing protein sequences.
        save_file (str): Path to save the generated embeddings.
        seq_length (int, optional): Maximum sequence length for the embeddings. Defaults to 1022.
        max_tokens (int, optional): Maximum tokens per inference batch. Defaults to 2048.

    Returns
    -------
        None
    """
    if not torch.cuda.is_available():
        raise RuntimeError("Protein embedding generation requires CUDA; refusing to write an empty output")
    if max_tokens < 1:
        raise ValueError("max_tokens must be positive")
    if not model_sha256 or not source_sha256:
        raise ValueError("A model checkpoint hash and source FASTA hash are required")

    save_dir = os.path.dirname(save_file)
    if save_dir and not os.path.exists(save_dir):
        os.makedirs(save_dir)

    dataset = FastaBatchedDataset.from_file(fasta)
    dataset.sequence_strs = [clean_sequence(seq) for seq in dataset.sequence_strs]

    batches = dataset.get_batch_indices(max_tokens, extra_toks_per_seq=1)

    data_loader = torch.utils.data.DataLoader(
        dataset,
        collate_fn=alphabet.get_batch_converter(seq_length),
        batch_sampler=batches,
        num_workers=0,
    )

    run = {
        "format": 1,
        "source_url": source_url,
        "source_sha256": source_sha256,
        "fasta_sha256": sha256_file(fasta),
        "model_name": model_name,
        "model_sha256": model_sha256,
        "esm_version": getattr(esm, "__version__", "unknown"),
        "layer": layer,
        "seq_length": seq_length,
        "max_tokens": max_tokens,
        "batch_count": len(batches),
    }
    identity = hashlib.sha256(json.dumps(run, sort_keys=True).encode("utf-8")).hexdigest()
    if os.path.exists(save_file):
        with h5py.File(save_file, "r") as existing:
            if existing.attrs.get("identity") != identity or not existing.attrs.get("complete", False):
                raise RuntimeError(f"Existing output belongs to another or incomplete run: {save_file}")
        logging.info("Completed output already exists: %s", save_file)
        return

    parts_dir = Path(save_file + ".parts")
    parts_dir.mkdir(exist_ok=True)
    manifest = parts_dir / "manifest.json"
    if manifest.exists():
        with open(manifest, encoding="utf-8") as source:
            if json.load(source) != run:
                raise RuntimeError(f"Resume metadata differs; use a different output path: {parts_dir}")
    elif any(path.name != "manifest.json.tmp" for path in parts_dir.iterdir()):
        raise RuntimeError(f"Unidentified partial output exists: {parts_dir}")
    else:
        atomic_json(manifest, run)

    gene_ids = []
    seen_genes = set()
    chunks = []
    chunk_expectations = []
    num_gpus = torch.cuda.device_count()
    with torch.no_grad():
        for batch_idx, (labels, strs, toks) in enumerate(data_loader):
            chunk_path = parts_dir / f"batch_{batch_idx:08d}.h5"
            expected_labels = [label.split()[0] for label in labels]
            for gene_id in expected_labels:
                if gene_id not in seen_genes:
                    seen_genes.add(gene_id)
                    gene_ids.append(gene_id)
            if chunk_path.exists():
                if not completed_chunk(chunk_path, identity, batch_idx, expected_labels):
                    raise RuntimeError(f"Invalid completed chunk; inspect before resuming: {chunk_path}")
                chunks.append(chunk_path)
                chunk_expectations.append((chunk_path, batch_idx, expected_labels))
                continue
            logging.info("Processing batch %d of %d", batch_idx + 1, len(batches))
            toks = pad_batch(toks, num_gpus).to(device="cuda", non_blocking=True)
            out = model(toks, repr_layers=[layer], return_contacts=False)
            representations = out["representations"][layer].to(device="cpu")
            vectors = []
            for i, sequence in enumerate(strs):
                truncate_len = min(seq_length, len(sequence))
                vectors.append(representations[i, 1 : truncate_len + 1].mean(0).numpy())
            publish_chunk(chunk_path, identity, batch_idx, expected_labels, vectors)
            chunks.append(chunk_path)
            chunk_expectations.append((chunk_path, batch_idx, expected_labels))

    if not chunks:
        raise RuntimeError("Input FASTA contains no protein sequences")
    for chunk_path, batch_idx, expected_labels in chunk_expectations:
        if not completed_chunk(chunk_path, identity, batch_idx, expected_labels):
            raise RuntimeError(f"Chunk changed or is incomplete: {chunk_path}")
    publish_gene_embeddings(save_file, chunks, identity, gene_ids)


def main():
    parser = argparse.ArgumentParser(description="Generate protein embeddings and convert to gene embeddings.")
    parser.add_argument(
        "--output_dir",
        type=str,
        default="./",
        required=False,
        help="Directory to save output files",
    )
    parser.add_argument(
        "--max_tokens", type=int, default=2048, help="Maximum ESM-2 tokens per inference batch"
    )
    parser.add_argument(
        "--organism_key",
        type=str,
        default="homo_sapiens",
        help="The organism key to generate protein embeddings for",
    )
    parser.add_argument(
        "--use_large_model",
        action="store_true",
        help="Whether to use the large ESM-2 model",
    )
    args = parser.parse_args()

    if not torch.cuda.is_available():
        parser.error("Protein embedding generation requires CUDA; no output was written")
    if args.max_tokens < 1:
        parser.error("--max_tokens must be positive")

    logging.basicConfig(level=logging.INFO)

    # Load FASTA URL manifest
    with open(FASTA_MANIFEST) as f:
        fasta_urls = json.load(f)

    if args.organism_key not in fasta_urls:
        raise ValueError(f"Organism {args.organism_key} is not a valid organism in the fasta manifest")

    # Create stable_id_dir if it doesn't exist
    stable_id_dir = Path(STABLE_ID_DIR)
    stable_id_dir.mkdir(parents=True, exist_ok=True)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load ESM-2 model
    if args.use_large_model:
        model, alphabet = esm.pretrained.esm2_t48_15B_UR50D()
        suffix = "_large"
        model_name = "esm2_t48_15B_UR50D"
        layer = 48
    else:
        model, alphabet = esm.pretrained.esm2_t36_3B_UR50D()
        suffix = ""
        model_name = "esm2_t36_3B_UR50D"
        layer = 33

    checkpoint = Path(torch.hub.get_dir()) / "checkpoints" / f"{model_name}.pt"
    if not checkpoint.is_file():
        raise RuntimeError(f"Cannot fingerprint ESM-2 checkpoint: {checkpoint}")
    model_sha256 = sha256_file(checkpoint)

    model.eval()  # disables dropout for deterministic results
    if torch.cuda.is_available():
        model = model.cuda()

    if torch.cuda.device_count() > 1:
        model = torch.nn.DataParallel(model)

    organism = args.organism_key
    fasta_url = fasta_urls[organism]["fa"]

    fasta_file = stable_id_dir / f"{organism}.fa"
    if not fasta_file.exists():
        logging.info(f"Downloading FASTA for {organism}")
        temporary = fasta_file.with_name(fasta_file.name + ".tmp")
        with urllib.request.urlopen(fasta_url) as response, open(temporary, "wb") as out_file:
            if fasta_url.endswith(".gz") or response.headers.get("Content-Encoding") == "gzip":
                with gzip.GzipFile(fileobj=response) as gz_file:
                    shutil.copyfileobj(gz_file, out_file)
            else:
                shutil.copyfileobj(response, out_file)
            out_file.flush()
            os.fsync(out_file.fileno())
        os.replace(temporary, fasta_file)
    source_sha256 = sha256_file(fasta_file)

    # Convert to gene IDs
    converted_fasta = stable_id_dir / f"{organism}_gene_input.fa"
    converted_tmp = converted_fasta.with_name(converted_fasta.name + ".tmp")
    with open(converted_tmp, "w", encoding="utf-8") as output:
        for record in SeqIO.parse(fasta_file, "fasta"):
            if args.use_large_model and "gene_symbol:" in record.description:
                gene_id = record.description.split("gene_symbol:")[-1].split(" ")[0].strip()
            else:
                if "gene:" not in record.description:
                    raise ValueError(
                        f"{organism}: protein {record.id} has no gene: field; "
                        "provide a verified protein-to-gene bridge before embedding generation"
                    )
                gene_id = record.description.split("gene:")[-1].split(" ")[0].strip().split(".")[0]
            if not gene_id:
                raise ValueError(f"{organism}: protein {record.id} has an empty gene key")
            record.id = gene_id
            record.name = gene_id
            record.description = gene_id
            SeqIO.write(record, output, "fasta")
        output.flush()
        os.fsync(output.fileno())
    os.replace(converted_tmp, converted_fasta)

    emb_file_name = output_dir / f"{organism}_gene{suffix}.h5"
    logging.info(f"Processing {converted_fasta} for {organism}")

    generate_embeddings(
        model,
        alphabet,
        str(converted_fasta),
        save_file=str(emb_file_name),
        max_tokens=args.max_tokens,
        model_name=model_name,
        model_sha256=model_sha256,
        source_sha256=source_sha256,
        source_url=fasta_url,
        layer=layer,
    )


if __name__ == "__main__":
    main()
