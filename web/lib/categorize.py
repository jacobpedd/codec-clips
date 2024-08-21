from google.cloud import language_v1
from django.conf import settings


gcloud = language_v1.LanguageServiceClient(
    client_options={"api_key": settings.GCLOUD_API_KEY}
)


def get_categories(text: str) -> list:
    document = language_v1.Document(
        content=text, type_=language_v1.Document.Type.PLAIN_TEXT
    )

    # Make a request to analyze the sentiment of the text.
    response = gcloud.classify_text(
        request={
            "document": document,
            "classification_model_options": {
                "v2_model": {
                    "content_categories_version": language_v1.ClassificationModelOptions.V2Model.ContentCategoriesVersion.V2
                }
            },
        }
    )

    return response.categories
