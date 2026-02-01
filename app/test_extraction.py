"""
Test script for the KYC extraction pipeline
Run this to verify the system works end-to-end
"""

import asyncio
import json
from extractor import KYCExtractor
from validator import KYCValidator
from pdf_filler import KYCPDFFiller
from emailer import send_kyc_email_test


# Sample Russian transcript for testing
SAMPLE_TRANSCRIPT_RU = """
Добрый день! Меня зовут Иван Сергеевич Петренко.

Да, я живу в Калгари, Альберта. Мой адрес: 123 Main Street Northwest,
квартира 456, почтовый код T2P 1J9.

Мой телефон 403-555-1234, а мобильный 403-555-5678.
Электронная почта ivan.petrenko@gmail.com

Мне 44 года, я родился 15 января 1980 года. Я женат, у нас двое детей.

Я работаю программистом в компании Tech Solutions уже 8 лет.
Моя жена Анна работает бухгалтером в небольшой фирме.

Мой годовой доход примерно 180 тысяч долларов до налогов.
Жена зарабатывает около 75 тысяч в год.
Доход стабильный последние несколько лет.

У нас есть сбережения около 400 тысяч в банке и инвестициях.
Также есть дом, который стоит примерно 850 тысяч.
Ипотека осталась около 200 тысяч.

Я хочу инвестировать на долгий срок - планирую выйти на пенсию лет через 15-20.
Готов к умеренному риску. Не хочу слишком рисковать, но понимаю что нужен рост.
Моя цель - рост капитала с небольшим доходом.

У меня есть опыт инвестирования - владею акциями и ETF фондами.
Раньше инвестировал в криптовалюту, но сейчас нет.

Нет, я не политик и не работаю в международных организациях.
Никогда не занимал государственных должностей.
"""

SAMPLE_TRANSCRIPT_EN = """
Hello, my name is John Michael Smith.

I live at 456 Oak Avenue, Unit 12, Toronto, Ontario, M5V 2K7.
My phone number is 416-555-9876 and my email is john.smith@email.com

I'm 52 years old, born on March 22, 1973. I'm married with one child.

I'm a Financial Analyst at Big Bank Corporation, been there for 12 years.
My wife Sarah is a nurse at Toronto General Hospital.

My annual salary is about $145,000 before taxes.
My wife makes around $95,000 per year.
Our income has been stable for the past 5 years.

We have approximately $800,000 in financial assets - stocks, bonds, and savings.
Our home is worth about $1.2 million with a mortgage of $350,000.
We also have a rental property worth $600,000 with $200,000 mortgage remaining.

I'm looking to invest for the long term, probably 10+ years until retirement.
I have a moderate to high risk tolerance - I understand markets fluctuate.
My main goal is growth, I don't need income from these investments.

I have good investment knowledge - I've been investing for 20 years.
I currently own stocks, mutual funds, and some REITs.

No, I'm not a politically exposed person and never held government positions.
"""


async def test_full_pipeline(transcript: str, language: str = "auto"):
    """Test the full extraction pipeline"""

    print("=" * 60)
    print("SKYVAULT KYC EXTRACTION TEST")
    print("=" * 60)

    # Step 1: Extract
    print("\n[1/4] Extracting data from transcript...")
    extractor = KYCExtractor()

    try:
        extracted = await extractor.extract(transcript, language, "individual")
        print("✅ Extraction complete")
        print(f"   Client: {extracted.get('client_name', {}).get('first', '?')} {extracted.get('client_name', {}).get('last', '?')}")
    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        return

    # Step 2: Validate
    print("\n[2/4] Validating extracted data...")
    validator = KYCValidator()
    validation = validator.validate(extracted, "individual")

    print(f"✅ Validation complete")
    print(f"   Exemption Status: {validation.exemption_status}")
    print(f"   Red Flags: {len(validation.red_flags)}")
    print(f"   Warnings: {len(validation.warnings)}")
    print(f"   Missing Fields: {len(validation.missing_required)}")

    # Step 3: Generate PDF
    print("\n[3/4] Generating PDF...")
    filler = KYCPDFFiller()

    try:
        pdf_path = filler.fill(extracted, "individual")
        print(f"✅ PDF generated: {pdf_path}")
    except FileNotFoundError as e:
        print(f"⚠️ PDF generation skipped (template not found)")
        pdf_path = None
    except Exception as e:
        print(f"❌ PDF generation failed: {e}")
        pdf_path = None

    # Step 4: Generate email preview
    print("\n[4/4] Generating email preview...")
    email_path = send_kyc_email_test(extracted, validation.to_dict(), pdf_path, "individual")
    print(f"✅ Email preview saved: {email_path}")

    # Print summary
    print("\n" + "=" * 60)
    print("EXTRACTION SUMMARY")
    print("=" * 60)
    print(json.dumps(extracted, indent=2, ensure_ascii=False, default=str))

    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    print(json.dumps(validation.to_dict(), indent=2))

    return extracted, validation


def test_quick_extract(transcript: str):
    """Test quick extraction for webhook response"""

    async def run():
        extractor = KYCExtractor()
        result = await extractor.quick_extract(transcript)
        print("Quick Extract Result:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return result

    return asyncio.run(run())


if __name__ == "__main__":
    import sys

    print("Select test:")
    print("1. Russian transcript (full pipeline)")
    print("2. English transcript (full pipeline)")
    print("3. Quick extract test (Russian)")
    print("4. Quick extract test (English)")

    choice = input("\nEnter choice (1-4): ").strip() or "1"

    if choice == "1":
        asyncio.run(test_full_pipeline(SAMPLE_TRANSCRIPT_RU, "ru"))
    elif choice == "2":
        asyncio.run(test_full_pipeline(SAMPLE_TRANSCRIPT_EN, "en"))
    elif choice == "3":
        test_quick_extract(SAMPLE_TRANSCRIPT_RU)
    elif choice == "4":
        test_quick_extract(SAMPLE_TRANSCRIPT_EN)
    else:
        print("Invalid choice")
