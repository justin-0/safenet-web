# from transformers import pipeline
#
# classifier = pipeline(
#     "text-classification",
#     model=r"D:\Riss_Projects_2025-26\FISAT MCA\safenet_ai_web\myapp\hate_speech_detector"
# )
#
# def detect_toxic_comment(comment):
#
#     result = classifier(comment)[0]
#
#     label = result['label']
#     score = result['score']
#
#     if label == "LABEL_2":
#         toxicity = "Hate Speech"
#     elif label == "LABEL_1":
#         toxicity = "Offensive"
#     else:
#         toxicity = "Non-Toxic"
#
#     return toxicity, score
#
#
# if __name__ == "__main__":
#
#     print("💬 English Toxic Comment Detector")
#     print("Type 'exit' to quit\n")
#
#     while True:
#
#         text = input("Enter comment: ")
#
#         if text.lower() == "exit":
#             print("👋 Exiting...")
#             break
#
#         result, confidence = detect_toxic_comment(text)
#
#         print("⚠️ Result:", result)
#         print("📊 Confidence:", round(confidence, 4))
#         print("-" * 40)




from detoxify import Detoxify

model = Detoxify('unbiased')

def detect_toxic_comment(comment):

    result = model.predict(comment)

    toxicity_score = result['toxicity']
    insult_score = result['insult']
    obscene_score = result['obscene']
    threat_score = result['threat']
    identity_score = result['identity_attack']

    max_score = max(
        toxicity_score,
        insult_score,
        obscene_score,
        threat_score,
        identity_score
    )

    if max_score > 0.7:
        label = "Offensive"
    else:
        label = "Non-Toxic"

    return label, max_score