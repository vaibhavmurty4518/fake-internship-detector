"""
test_examples.py
-----------------
Runs 5 representative example postings through the SAME prediction
pipeline used by the Streamlit app (inference.predict). Outputs are
generated live by the trained model + rule-based feature extractor —
nothing here is hand-edited to "look right".

Run: python test_examples.py   (after train_model.py has been run once)
"""

from inference import predict

EXAMPLES = [
    {
        "label": "1. Clearly legitimate-looking internship",
        "text": """Software Engineering Intern - Backend Team
About Us: We are a Series B fintech company headquartered in Bengaluru,
founded in 2018, building payment infrastructure for small businesses.
Learn more at www.examplefintech.com/about.
Role: You will work with our backend engineering team on our Python/Django
services, write unit tests, and participate in code reviews. This is a
6-month paid internship (stipend Rs 20,000/month) with the possibility of
a full-time offer based on performance.
Requirements: Currently pursuing a B.Tech/B.E in Computer Science or
related field, familiarity with Python and REST APIs, good communication
skills. Please apply through our official careers page or email your
resume to careers@examplefintech.com.""",
    },
    {
        "label": "2. Registration fee scam",
        "text": """URGENT HIRING!!! Work From Home Data Entry Internship
Earn Rs 45,000 per month, no experience needed!
Limited seats available, apply today before offer ends!
To confirm your selection, candidates must pay a refundable registration
fee of Rs 999. Contact us immediately on WhatsApp for further details.
Email: hrjobs2024@gmail.com""",
    },
    {
        "label": "3. Unrealistic stipend",
        "text": """Marketing Intern - Immediate Joining
Fresher welcome, no experience or interview required.
Guaranteed income of Rs 80,000 per month, 100% job guarantee!
Work only 2 hours a day from home. Apply now, seats filling fast!
Contact: marketingjobs99@yahoo.com""",
    },
    {
        "label": "4. Urgency-based suspicious posting",
        "text": """Hiring Interns - Apply Immediately!!!
Only 3 seats left, hurry up, don't miss this opportunity!
Great exposure, certificate provided. Apply today, last date is tomorrow!
For more info WhatsApp us at the number in the flyer. Act now!""",
    },
    {
        "label": "5. Mixed / somewhat suspicious posting",
        "text": """HR Intern needed for a growing startup.
Remote work from home, flexible hours, stipend Rs 8,000/month.
We are a small team building a new app. No formal company website yet
but you can reach out over WhatsApp or personal email for details:
recruiter123@gmail.com. Interested candidates apply today, limited slots.""",
    },
]


def main():
    print("=" * 70)
    print("FAKE INTERNSHIP DETECTOR — TEST EXAMPLES")
    print("(live predictions from the trained model, not hand-crafted)")
    print("=" * 70)

    for ex in EXAMPLES:
        result = predict(ex["text"])
        print(f"\n{ex['label']}")
        print("-" * len(ex["label"]))
        print(f"Risk Level : {result['risk_level']}")
        print(f"Risk Score : {result['risk_score']}%")
        if result["indicators"]:
            print("Indicators :")
            for ind in result["indicators"]:
                print(f"   • {ind['title']}")
        else:
            print("Indicators : none detected")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
