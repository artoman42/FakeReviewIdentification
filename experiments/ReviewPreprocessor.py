import polars as pl
import spacy_udpipe
import string

class UkrainianReviewPreprocessor:
    def __init__(self, model_lang: str = 'uk', stopwords: set = None):
        self.nlp = spacy_udpipe.load(model_lang)
        
        if stopwords is not None:
            self.stopwords = set(stopwords)

    def preprocess_text(self, text: str) -> list:
        text = text.strip()
        doc = self.nlp(text)
        tokens = []
        for token in doc:
           
            if token.text in string.punctuation:
                continue
            token_text = token.lemma_.lower().strip()
            if not token_text or token_text in self.stopwords or token_text.isdigit():
                continue
            tokens.append(token_text)
        return tokens

    def preprocess_dataframe(self, 
                             df: pl.DataFrame, 
                             review_column: str = "відгук", 
                             tokens_column: str = "токени", 
                             joined_column: str = "токенізований_рядок") -> pl.DataFrame:
        df = df.with_columns(
            pl.col(review_column).map_elements(lambda x: self.preprocess_text(x),return_dtype=pl.List(pl.String)).alias(tokens_column)
        )
        df = df.with_columns(
            pl.col(tokens_column).map_elements(lambda tokens: " ".join(tokens), return_dtype=pl.String).alias(joined_column)
        )
        return df

    def get_tfidf_input(self, df: pl.DataFrame, joined_column: str = "токенізований_рядок") -> list:
        return df[joined_column].to_list()

class UkrainianReviewPreprocessor:
    def __init__(self, model_lang: str = 'uk', stopwords: set = None):
        """
        Initialize the preprocessor.
        
        :param model_lang: Language code for the UDPipe model. Default 'uk' for Ukrainian.
        :param stopwords: Optional set of stopwords to filter out.
        """
        # Load the Ukrainian UDPipe model using spaCy‑UDPipe
        self.nlp = spacy_udpipe.load(model_lang)
        # Use provided stopwords or a minimal default list (expand this list as needed)
        if stopwords is not None:
            self.stopwords = set(stopwords)
        else:
            self.stopwords = {
                "і", "та", "але", "що", "це", "від", "з", "на", "до", "як", "такий", "чи"
            }

    def preprocess_text(self, text: str) -> list:
        """
        Process a single review text: tokenization, lemmatization, lowercasing,
        and filtering of punctuation, stopwords, and numeric tokens.
        
        :param text: The review text.
        :return: A list of processed tokens.
        """
        # Basic cleanup: strip extra whitespace
        text = text.strip()
        # Process text with spaCy‑UDPipe
        doc = self.nlp(text)
        tokens = []
        for token in doc:
            # Skip tokens that are pure punctuation
            if token.text in string.punctuation:
                continue
            # Get the lemma, lowercase it, and strip extra spaces
            token_text = token.lemma_.lower().strip()
            # Skip if the token is empty, a stopword, or purely numeric
            if not token_text or token_text in self.stopwords or token_text.isdigit():
                continue
            tokens.append(token_text)
        return tokens

    def preprocess_dataframe(self, 
                             df: pl.DataFrame, 
                             review_column: str = "відгук", 
                             tokens_column: str = "токени", 
                             joined_column: str = "токенізований_рядок") -> pl.DataFrame:
        """
        Preprocess reviews in a Polars DataFrame.
        
        :param df: Polars DataFrame containing reviews.
        :param review_column: Column name containing review text.
        :param tokens_column: Column name to store the list of tokens.
        :param joined_column: Column name to store the joined tokens string.
        :return: A Polars DataFrame with new columns for tokens and joined tokens.
        """
        # Apply preprocessing on the review_column
        df = df.with_columns(
            pl.col(review_column).map_elements(lambda x: self.preprocess_text(x),return_dtype=pl.List(pl.String)).alias(tokens_column)
        )
        # Join tokens into a single string for TF‑IDF vectorization
        df = df.with_columns(
            pl.col(tokens_column).map_elements(lambda tokens: " ".join(tokens), return_dtype=pl.String).alias(joined_column)
        )
        return df

    def get_tfidf_input(self, df: pl.DataFrame, joined_column: str = "токенізований_рядок") -> list:
        """
        Get a list of joined token strings from the DataFrame for TF‑IDF vectorization.
        
        :param df: Polars DataFrame with a column of joined token strings.
        :param joined_column: Column name containing joined tokens.
        :return: List of strings.
        """
        return df[joined_column].to_list()