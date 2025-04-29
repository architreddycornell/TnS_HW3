import pandas as pd
import sys, re
from typing import Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
from pathlib import Path


try:

    from atproto import Client
    _ATP_CLIENT = Client()

except ImportError:
    _ATP_CLIENT = None




class PolicyProposalClassifier:
    def __init__(self):
        #self.train_data = pd.read_csv('training-data/posts.csv')
        
        root = Path(__file__).resolve().parent

        csv_path = root.parent / "training-data" / "posts.csv"

        self.train_data = pd.read_csv(csv_path)
        
        self.vectorizer = TfidfVectorizer(max_features=5000)
        self.model = LogisticRegression()

        self.train_data['Post'] = self.train_data['Post'].fillna('')

        # Split the data into training and testing sets
        self.X_train, self.X_test, self.y_train, self.y_test = train_test_split(
            self.train_data['Post'], 
            self.train_data['Label'], 
            test_size=0.2, 
            random_state=42
        )

        # Fit the model
        self.X_tfidf = self.vectorizer.fit_transform(self.X_train)
        self.model.fit(self.X_tfidf, self.y_train)

        # Transform the test data
        self.X_test_tfidf = self.vectorizer.transform(self.X_test)
        # Make predictions
        self.y_pred = self.model.predict(self.X_test_tfidf)

    def train(self, texts, labels):
        self.vectorizer.fit_transform(texts)
        
    def predict(self, text):
        X_tfidf = self.vectorizer.transform([text])
        prediction = self.model.predict(X_tfidf)
        return prediction[0]
    
    def evaluate(self):
        print("Accuracy:", accuracy_score(self.y_test, self.y_pred))
        return classification_report(self.y_test, self.y_pred)


def post_text_from_url(url: str) -> Optional[str]:

    if _ATP_CLIENT is None:

        return None
    
    try:

        rkey = url.rstrip("/").split("/")[-1]

        handle = url.split("/")[-3]

        post = _ATP_CLIENT.get_post(rkey, handle)

        return post.value.text or ""

    except Exception as exc:

        print(f"Warning: Couldn't fetch post text : {exc}")

        return None
# use the classifier

if __name__ == "__main__":

    if len(sys.argv) < 2:

        print("Usage: python3 policy_proposal_labeler.py <post-url>")


    user_input = " ".join(sys.argv[1:])

    is_url = re.match(r"https?://", user_input)

    if is_url:

        text = post_text_from_url(user_input)

        if not text:

            sys.exit("Unable to fetch posts")

    else:

        text = user_input

    
    classifier = PolicyProposalClassifier()

    label = classifier.predict(text)

    print(f"Input text:\n {text[:120]}...\nPrediction -> {label}")

    if label == 1:

        print("POTENTIAL-SCAM")


    print("\n=== model evaluation on hold")

    print(classifier.evaluate())