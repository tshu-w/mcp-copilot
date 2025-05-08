import bm25s
import Stemmer


class SparseRetriever:
    def __init__(
        self,
        stopwords: str | list[str] = "english",
        stemmer: str | None = "english",
    ):
        """
        Initialize a sparse retriever for document search.

        Args:
            stopwords (str | list[str]): Either a string specifying a predefined stopwords set
                                         (e.g., "english") or a list of custom stopwords.
                                         Default is "english".
            stemmer (str | None): The language for the stemmer (e.g., "english", "german").
                                  If None, no stemming will be applied. Default is "english".
        """
        self.stopwords = stopwords
        self.stemmer = Stemmer.Stemmer(stemmer) if stemmer else None
        self.retriever = bm25s.BM25()

    def index(self, corpus: list[dict]) -> "SparseRetriever":
        """
        Index a corpus of documents for later retrieval.

        Args:
            corpus (list[dict]): List of dictionaries where each dictionary represents a document
                                 with at least 'id' and 'text' keys.

        Returns:
            SparseRetriever: The current instance with the indexed corpus.
        """
        self.doc_ids = []
        corpus_texts = []
        for doc in corpus:
            self.doc_ids.append(doc["id"])
            corpus_texts.append(doc["text"])

        corpus_tokens = bm25s.tokenize(
            corpus_texts,
            stopwords=self.stopwords,
            stemmer=self.stemmer,
        )
        self.retriever.index(corpus_tokens)

        return self

    def search(self, query: str, top_k: int) -> list[dict]:
        """
        Search the indexed corpus for the most relevant documents.

        Args:
            query (str): The search query.
            top_k (int): The number of top results to return.

        Returns:
            list[dict]: A list of dictionaries containing the top-k search results,
                       each with 'doc_id' and 'score' fields.
        """
        query_tokens = bm25s.tokenize(
            query,
            stopwords=self.stopwords,
            stemmer=self.stemmer,
        )
        results, scores = self.retriever.retrieve(
            query_tokens,
            k=min(top_k, len(self.doc_ids)),
        )

        return [
            {
                "doc_id": self.doc_ids[idx],
                "score": score,
            }
            for idx, score in zip(results[0].tolist(), scores[0].tolist(), strict=False)
        ]


if __name__ == "__main__":
    collection = [
        {"id": "doc_1", "text": "Generals gathered in their masses"},
        {"id": "doc_2", "text": "Just like witches at black masses"},
        {"id": "doc_3", "text": "Evil minds that plot destruction"},
        {"id": "doc_4", "text": "Sorcerer of death's construction"},
    ]
    retriever = SparseRetriever().index(collection)
    query = "witches masses"
    top_k = 2
    print(retriever.search(query, top_k))
