"""
GitHub Service for creating issues using PyGithub
"""

import os
from typing import Dict, Optional, Any, List
from github import Github
from github.Issue import Issue
from loguru import logger


class GitHubService:
    """Service for interacting with GitHub repositories"""

    def __init__(self):
        """Initialize GitHub service with environment variables"""
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.repository_name = os.getenv("GITHUB_REPOSITORY")  # Format: "owner/repo"

        if not self.github_token:
            logger.warning("GITHUB_TOKEN not found in environment variables")
            self.github = None
            self.repository = None
        else:
            try:
                print(f"GITHUB_TOKEN: {self.github_token}")
                print(f"GITHUB_REPOSITORY: {self.repository_name}")
                self.github = Github(self.github_token)
                if self.repository_name:
                    self.repository = self.github.get_repo(self.repository_name)
                    logger.info(f"GitHub service initialized for repository: {self.repository_name}")
                else:
                    logger.warning("GITHUB_REPOSITORY not found in environment variables")
                    self.repository = None
            except Exception as e:
                logger.error(f"Failed to initialize GitHub service: {e}")
                self.github = None
                self.repository = None

    def is_configured(self) -> bool:
        """Check if GitHub service is properly configured"""
        return self.github is not None and self.repository is not None

    async def create_issue(self, title: str, body: str, labels: Optional[list] = None, assignees: Optional[list] = None) -> Dict[str, Any]:
        """
        Create a new GitHub issue

        Args:
            title: Issue title
            body: Issue description/body
            labels: List of label names to add to the issue
            assignees: List of usernames to assign to the issue

        Returns:
            Dictionary with success status and issue data
        """
        if not self.is_configured():
            return {"success": False, "error": "GitHub service not properly configured", "issue_url": None, "issue_number": None}

        try:
            # Create the issue
            issue: Issue = self.repository.create_issue(title=title, body=body, labels=labels or [], assignees=assignees or [])

            logger.info(f"Successfully created GitHub issue #{issue.number}: {title}")

            return {"success": True, "issue_url": issue.html_url, "issue_number": issue.number, "issue_id": issue.id}

        except Exception as e:
            logger.error(f"Failed to create GitHub issue: {e}")
            return {"success": False, "error": str(e), "issue_url": None, "issue_number": None}

    async def create_feedback_issue(
        self,
        feedback_type: str,
        user_name: str,
        user_email: str,
        description: str,
        base_url: str,
        feedback_id: Optional[int] = None,
        checkin_id: Optional[int] = None,
        image_urls: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Create a GitHub issue from user feedback
        """
        title_parts = [f"Feedback from {user_name}"]
        title = " ".join(title_parts)

        body_parts = [
            f"**Feedback Type:** {feedback_type.title()}",
            f"**User:** {user_name} ({user_email})",
            "",
            "**Description:**",
            description,
            "",
        ]

        if feedback_id:
            body_parts.append(f"**Feedback ID:** {feedback_id}")

        if checkin_id:
            body_parts.append(f"**Check-in ID:** {checkin_id}")

        if image_urls:
            body_parts.extend(["", "**Images:**"])
            for url in image_urls:
                body_parts.append(f"![feedback image]({url})")
                body_parts.append(url)

        body_parts.extend(["", f"**Dashboard Link:** {base_url}/dashboard"])
        body_parts.extend(["", "---", "*This issue was automatically created from user feedback.*"])

        body = "\n".join(body_parts)
        labels = [feedback_type.lower()]

        return await self.create_issue(title=title, body=body, labels=labels)


# Global GitHub service instance
github_service = GitHubService()
