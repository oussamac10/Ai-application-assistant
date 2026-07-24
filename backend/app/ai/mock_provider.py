import re
from typing import Protocol

from app.ai.schemas import ExtractionRequest, ExtractionResult


class AIProvider(Protocol):
    async def extract_value(
        self,
        request: ExtractionRequest,
    ) -> ExtractionResult: ...


class MockAIProvider:
    async def extract_value(
        self,
        request: ExtractionRequest,
    ) -> ExtractionResult:
        field_type = request.field_type
        answer = request.answer.strip()

        if field_type == "person_name":
            return ExtractionResult(
                normalizedValue={"fullName": answer},
                outputValue=answer,
                requiresClarification=False,
                uncertainties=[],
            )

        elif field_type == "money":
            # If the answer is just digits, trigger clarification
            if re.match(r"^\d+$", answer):
                return ExtractionResult(
                    normalizedValue={"amount": int(answer)},
                    outputValue=None,
                    requiresClarification=True,
                    uncertainties=["currency", "period"],
                )
            else:
                # Extract digits
                digits = "".join([c for c in answer if c.isdigit()])
                amount = int(digits) if digits else 1800
                currency = "EUR"
                if "USD" in answer.upper() or "$" in answer:
                    currency = "USD"
                period = "monthly"
                if "YEAR" in answer.upper() or "ANNUAL" in answer.upper():
                    period = "yearly"

                return ExtractionResult(
                    normalizedValue={
                        "amount": amount,
                        "currency": currency,
                        "period": period,
                    },
                    outputValue=f"{amount} {currency} {period}",
                    requiresClarification=False,
                    uncertainties=[],
                )

        elif field_type == "date":
            return ExtractionResult(
                normalizedValue=answer,
                outputValue=answer,
                requiresClarification=False,
                uncertainties=[],
            )

        # For everything else, default
        return ExtractionResult(
            normalizedValue=answer,
            outputValue=answer,
            requiresClarification=False,
            uncertainties=[],
        )
