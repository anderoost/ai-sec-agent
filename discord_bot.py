#!/usr/bin/env python3
"""
Discord Security Assessment Bot
Integrates with the security assessment agent to provide:
1. Draw.io diagram security assessments
2. General security question answering
"""

import os
import asyncio
import tempfile
from pathlib import Path
from typing import Optional

import discord
from discord import File
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import our security assessment functions
from agent import (
    build_architecture_summary,
    format_assessment_prompt,
    parse_counts_and_percentages,
    build_report_markdown,
    run_pytm_model,
    local_llm_query
)

class SecurityBot(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.temp_dir = Path(tempfile.mkdtemp())

    async def on_ready(self):
        print(f'🤖 Security Bot logged in as {self.user}')

    async def on_message(self, message):
        # Don't respond to our own messages
        if message.author == self.user:
            return

        # Check if message mentions the bot or is a DM
        if isinstance(message.channel, discord.DMChannel) or self.user in message.mentions:
            await self.handle_security_query(message)
        elif message.attachments:
            # Check for Draw.io files
            for attachment in message.attachments:
                if attachment.filename.lower().endswith(('.drawio', '.xml')):
                    await self.handle_drawio_assessment(message, attachment)
                    break

    async def handle_drawio_assessment(self, message, attachment):
        """Handle Draw.io file assessment"""
        try:
            await message.channel.send("🔍 Analyzing Draw.io diagram for security assessment...")

            # Download the file
            file_path = self.temp_dir / attachment.filename
            await attachment.save(file_path)

            # Run security assessment
            await message.channel.send("📊 Building architecture summary...")
            architecture_summary = build_architecture_summary(file_path)

            # Generate assessment prompt
            prompt = format_assessment_prompt(architecture_summary)

            # Get AI assessment
            await message.channel.send("🧠 Running AI security analysis...")
            llm_output = local_llm_query(prompt, os.getenv("MODEL_PATH", "mock"))

            # Parse results
            parsed_data = parse_counts_and_percentages(llm_output)

            # Run PYTM analysis
            await message.channel.send("🎯 Running PYTM threat modeling...")
            pytm_results = run_pytm_model(file_path)

            # Build report
            await message.channel.send("📝 Generating security report...")
            report_text = build_report_markdown(file_path, architecture_summary, llm_output, parsed_data, pytm_results)

            # Save report
            report_path = self.temp_dir / f"security_report_{message.id}.md"
            report_path.write_text(report_text, encoding="utf-8")

            # Send report
            await message.channel.send(
                f"✅ Security assessment complete!\n\n**Summary:**\n"
                f"- **Threats Found:** {len(pytm_results.get('threats', []))}\n"
                f"- **High/Critical Threats:** {sum(1 for t in pytm_results.get('threats', []) if t.get('severity') in ['High', 'Very High'])}\n"
                f"- **Risk Score:** {self.calculate_risk_score(parsed_data, pytm_results)}/5",
                file=File(report_path, filename="security_report.md")
            )

        except Exception as e:
            await message.channel.send(f"❌ Error during assessment: {str(e)}")
        finally:
            # Cleanup
            if file_path.exists():
                file_path.unlink(missing_ok=True)

    async def handle_security_query(self, message):
        """Handle general security questions"""
        try:
            # Remove bot mention from message
            content = message.content.replace(f'<@{self.user.id}>', '').strip()

            if not content:
                await message.channel.send(
                    "👋 Hi! I can help with:\n\n"
                    "🔍 **Security Assessments:** Upload a Draw.io file for automated threat modeling\n"
                    "💬 **Security Questions:** Ask me about security tools, controls, best practices\n\n"
                    "Try: \"What WAF tools do you recommend for AWS?\" or \"How to secure AI applications?\""
                )
                return

            await message.channel.send("🤔 Thinking about your security question...")

            # Create a security-focused prompt
            prompt = f"""You are a cybersecurity expert. Answer this security question thoroughly and practically:

Question: {content}

Provide:
1. Direct answer with recommendations
2. Key considerations or requirements
3. Implementation steps (if applicable)
4. Additional resources or best practices

Be specific, actionable, and focus on current security standards."""

            # Get AI response
            response = local_llm_query(prompt, os.getenv("MODEL_PATH", "mock"), max_tokens=1500)

            # Send response (Discord has 2000 char limit, so chunk if needed)
            if len(response) <= 1900:
                await message.channel.send(response)
            else:
                # Split into chunks
                chunks = [response[i:i+1900] for i in range(0, len(response), 1900)]
                for i, chunk in enumerate(chunks):
                    if i == 0:
                        await message.channel.send(f"{chunk}...")
                    else:
                        await message.channel.send(f"...{chunk}")

        except Exception as e:
            await message.channel.send(f"❌ Error processing question: {str(e)}")

    def calculate_risk_score(self, parsed_data, pytm_results):
        """Calculate risk score based on threats and coverage"""
        counts = parsed_data["counts"]
        coverage = parsed_data["coverage"]

        total_threats = len(pytm_results.get("threats", []))
        high_severity = sum(1 for t in pytm_results.get("threats", [])
                          if t.get('severity') in ['High', 'Very High'])
        low_coverage = sum(1 for pct in coverage.values() if pct < 70)

        if total_threats == 0:
            return 1  # Very Low
        elif high_severity > 50 or low_coverage > 3:
            return 5  # Very High
        elif high_severity > 20 or low_coverage > 1:
            return 4  # High
        elif total_threats > 100 or low_coverage > 0:
            return 3  # Medium
        else:
            return 2  # Low


async def main():
    # Check for required environment variables
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        print("❌ Error: DISCORD_BOT_TOKEN environment variable not set")
        print("Please set your Discord bot token in the .env file")
        return

    # Create bot with intents
    intents = discord.Intents.default()
    intents.message_content = True

    bot = SecurityBot(intents=intents)

    try:
        await bot.start(token)
    except KeyboardInterrupt:
        await bot.close()
    finally:
        # Cleanup temp directory
        import shutil
        shutil.rmtree(bot.temp_dir, ignore_errors=True)


if __name__ == "__main__":
    asyncio.run(main())