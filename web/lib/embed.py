from fastembed import TextEmbedding


# NOTE: There doesn't seem to be a speed difference when we load from disk for each call
def get_embedding(text):
    embedding_model = TextEmbedding(model_name="nomic-ai/nomic-embed-text-v1.5-Q")

    embeddings_generator = embedding_model.embed(
        [text],
    )
    return list(embeddings_generator)[0]
