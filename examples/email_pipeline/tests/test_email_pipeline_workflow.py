"""Tests for EmailPipelineWorkflow integration."""

import pytest

from email_pipeline.workflows.email_pipeline_workflow import EmailPipelineWorkflow


@pytest.mark.asyncio
async def test_email_pipeline_personal_flow():
    """Test complete pipeline with personal email."""
    workflow = EmailPipelineWorkflow()

    input_data = {
        "email": {
            "from": "friend@gmail.com",
            "to": "user@example.com",
            "subject": "Hello",
            "body": "Hi there!",
            "attachments": [],
        }
    }

    result = await workflow.execute(input_data)

    # Verify validation passed
    assert result["valid"] is True
    # Verify security checks passed
    assert result["spam_check"]["is_spam"] is False
    assert result["virus_scan"]["is_safe"] is True
    # Verify routing to personal
    assert result["routing"]["email_type"] == "personal"
    # Verify personal handler executed
    assert result["handling"]["handler"] == "PersonalHandler"
    assert result["handling"]["folder"] == "Personal"


@pytest.mark.asyncio
async def test_email_pipeline_business_flow():
    """Test complete pipeline with business email."""
    workflow = EmailPipelineWorkflow()

    input_data = {
        "email": {
            "from": "ceo@company.com",
            "to": "user@example.com",
            "subject": "Meeting invitation",
            "body": "Let's discuss the proposal.",
            "attachments": [],
        }
    }

    result = await workflow.execute(input_data)

    # Verify routing to business
    assert result["routing"]["email_type"] == "business"
    # Verify business handler executed
    assert result["handling"]["handler"] == "BusinessHandler"
    assert result["handling"]["folder"] == "Business"
    assert result["handling"]["priority"] == "high"


@pytest.mark.asyncio
async def test_email_pipeline_parallel_security_checks():
    """Test that spam and virus checks run in parallel."""
    workflow = EmailPipelineWorkflow()

    input_data = {
        "email": {
            "from": "test@example.com",
            "to": "user@example.com",
            "subject": "Test",
            "body": "Test email",
            "attachments": [{"filename": "doc.pdf"}],
        }
    }

    result = await workflow.execute(input_data)

    # Both security checks should be present in result
    assert "spam_check" in result
    assert "virus_scan" in result
    assert result["spam_check"]["status"] == "checked"
    assert result["virus_scan"]["status"] == "scanned"
