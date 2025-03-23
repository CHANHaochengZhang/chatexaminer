#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
QuestionExperiment.py

This script analyzes exam questions using Bloom's Revised Taxonomy to evaluate
their quality and distribution across cognitive process dimensions.
"""

import argparse
import json
import math
import os
import time
from collections import Counter
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
import openai
import pandas as pd
import seaborn as sns
from scipy.stats import pearsonr

# Define cognitive process dimensions and their numeric levels
COGNITIVE_PROCESS = {
    "remember": 1,
    "understand": 2,
    "apply": 3,
    "analyze": 4,
    "evaluate": 5,
    "create": 6,
}

# Define knowledge dimensions
KNOWLEDGE_DIMENSIONS = ["factual", "conceptual", "procedural", "metacognitive"]

# Define target distribution for cognitive process dimensions
TARGET_DISTRIBUTION = {
    "remember": 0.15,
    "understand": 0.25,
    "apply": 0.25,
    "analyze": 0.20,
    "evaluate": 0.10,
    "create": 0.05,
}

# Group cognitive processes into Lower Order Thinking Skills (LOTS) and Higher Order Thinking Skills (HOTS)
LOTS = ["remember", "understand", "apply"]
HOTS = ["analyze", "evaluate", "create"]
TARGET_LOTS_RATIO = 0.65
TARGET_HOTS_RATIO = 0.35


class QuestionAnalyzer:
    """Class to analyze questions using Bloom's taxonomy"""

    def __init__(self, questions_file: str, api_key: str = None):
        """
        Initialize the question analyzer.

        Args:
            questions_file: Path to the JSON file containing exam questions
            api_key: OpenAI API key (optional, will use environment variable if not provided)
        """
        self.questions_file = questions_file
        self.questions = self._load_questions()

        # Set up OpenAI client if API key is provided
        self.client = None
        if api_key:
            self.client = openai.OpenAI(api_key=api_key)
        else:
            # Try to use environment variable
            try:
                self.client = openai.OpenAI()
            except:
                print(
                    "Warning: No OpenAI API key provided. Classification functionality will be limited."
                )

        # Will store classified questions
        self.classified_questions = []

    def _load_questions(self) -> Dict:
        """Load questions from JSON file"""
        with open(self.questions_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def classify_all_questions(self, model="gpt-4o") -> List[Dict]:
        """
        Classify all questions using OpenAI API

        Args:
            model: The OpenAI model to use for classification

        Returns:
            List of questions with classification data
        """
        if not self.client:
            print("Error: OpenAI client not initialized. Cannot classify questions.")
            return []

        classified = []

        # Process each question
        for q_id, question_data in self.questions.items():
            print(f"Classifying question {q_id}...")

            question_text = question_data["question"]
            difficulty = question_data.get("difficulty", 0)

            # Get classification from OpenAI
            classification = self._classify_question(question_text, model)

            # Add classification to question data
            classified_question = {
                "question_id": q_id,
                "question_text": question_text,
                "difficulty": difficulty,
                "classification": classification,
            }

            classified.append(classified_question)

            # Avoid rate limits
            time.sleep(1)

        self.classified_questions = classified
        return classified

    def _classify_question(self, question_text: str, model: str) -> Dict:
        """
        Classify a single question using OpenAI API

        Args:
            question_text: The question text to classify
            model: The OpenAI model to use

        Returns:
            Classification dictionary
        """
        prompt = f"""
        Please classify the following question according to Bloom's Revised Taxonomy:

        Question: {question_text}

        Please select the most appropriate category:
        1. Cognitive Process Dimension (select one): remember, understand, apply, analyze, evaluate, create
        2. Knowledge Dimension (select one): factual, conceptual, procedural, metacognitive

        Provide a brief explanation for your classification.

        Return ONLY your analysis in this exact JSON format without any additional text or explanation:
        {{
            "cognitive_process": "selected_cognitive_process",
            "knowledge_dimension": "selected_knowledge_dimension",
            "reasoning": "your reasoning"
        }}
        """

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an education assessment expert specializing in Bloom's Taxonomy. Return ONLY valid JSON without markdown formatting.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                response_format={"type": "json_object"},  # Request JSON format specifically
            )

            # Get response content
            content = response.choices[0].message.content
            print(f"Raw API response: {content[:100]}...")  # Print first 100 chars for debugging

            # Try to extract JSON from the response if not already valid JSON
            try:
                result = json.loads(content)
            except json.JSONDecodeError:
                # Try to find JSON by looking for { and } brackets
                import re

                json_match = re.search(r"({.*})", content, re.DOTALL)
                if json_match:
                    try:
                        result = json.loads(json_match.group(1))
                    except:
                        # If still can't parse, use a simple regex approach to extract fields
                        cognitive_match = re.search(r'"cognitive_process"\s*:\s*"([^"]+)"', content)
                        knowledge_match = re.search(
                            r'"knowledge_dimension"\s*:\s*"([^"]+)"', content
                        )
                        reasoning_match = re.search(r'"reasoning"\s*:\s*"([^"]+)"', content)

                        result = {
                            "cognitive_process": (
                                cognitive_match.group(1) if cognitive_match else "understand"
                            ),
                            "knowledge_dimension": (
                                knowledge_match.group(1) if knowledge_match else "conceptual"
                            ),
                            "reasoning": (
                                reasoning_match.group(1)
                                if reasoning_match
                                else "Extracted from non-JSON response"
                            ),
                        }
                else:
                    # Manual extraction failed, create default result with original content
                    result = {
                        "cognitive_process": "understand",
                        "knowledge_dimension": "conceptual",
                        "reasoning": f"Could not parse response: {content[:100]}...",
                    }

            # Normalize cognitive process to lowercase
            if "cognitive_process" in result:
                result["cognitive_process"] = result["cognitive_process"].lower()

            # Normalize knowledge dimension to lowercase
            if "knowledge_dimension" in result:
                result["knowledge_dimension"] = result["knowledge_dimension"].lower()

            return result

        except Exception as e:
            print(f"Error classifying question: {e}")
            # Return default classification if API call fails
            return {
                "cognitive_process": "understand",
                "knowledge_dimension": "conceptual",
                "reasoning": f"API error: {str(e)}",
            }

    def analyze_distribution(self) -> Dict:
        """
        Analyze the distribution of question classifications

        Returns:
            Dictionary with distribution analysis results
        """
        if not self.classified_questions:
            print("No classified questions available for analysis.")
            return {}

        # Count cognitive processes
        cognitive_counts = Counter(
            [q["classification"]["cognitive_process"] for q in self.classified_questions]
        )

        # Count knowledge dimensions
        knowledge_counts = Counter(
            [q["classification"]["knowledge_dimension"] for q in self.classified_questions]
        )

        # Calculate percentages
        total = len(self.classified_questions)
        cognitive_percentages = {
            category: count / total for category, count in cognitive_counts.items()
        }

        knowledge_percentages = {
            category: count / total for category, count in knowledge_counts.items()
        }

        # Calculate LOTS and HOTS percentages
        lots_percentage = sum([cognitive_percentages.get(cp, 0) for cp in LOTS])
        hots_percentage = sum([cognitive_percentages.get(cp, 0) for cp in HOTS])

        # Calculate quality metrics
        cs = self._calculate_coverage_score(cognitive_counts)
        sdi = self._calculate_shannon_diversity_index(cognitive_percentages)
        cc = self._calculate_consistency_coefficient()

        return {
            "cognitive_counts": dict(cognitive_counts),
            "cognitive_percentages": cognitive_percentages,
            "knowledge_counts": dict(knowledge_counts),
            "knowledge_percentages": knowledge_percentages,
            "lots_percentage": lots_percentage,
            "hots_percentage": hots_percentage,
            "hots_lots_ratio": (
                hots_percentage / lots_percentage if lots_percentage > 0 else float("inf")
            ),
            "quality_metrics": {
                "coverage_score": cs,
                "shannon_diversity_index": sdi,
                "consistency_coefficient": cc,
            },
        }

    def _calculate_coverage_score(self, cognitive_counts: Counter) -> float:
        """
        Calculate coverage score (CS) - percentage of cognitive categories covered

        Args:
            cognitive_counts: Counter object with cognitive process counts

        Returns:
            Coverage score as a percentage
        """
        categories_covered = len(cognitive_counts.keys())
        total_categories = len(COGNITIVE_PROCESS)
        return (categories_covered / total_categories) * 100

    def _calculate_shannon_diversity_index(self, percentages: Dict[str, float]) -> float:
        """
        Calculate Shannon Diversity Index (SDI) to measure distribution balance

        Args:
            percentages: Dictionary of category percentages

        Returns:
            Shannon Diversity Index value
        """
        sdi = 0
        for category in COGNITIVE_PROCESS.keys():
            p = percentages.get(category, 0)
            if p > 0:
                sdi -= p * math.log(p)
        return sdi

    def _calculate_consistency_coefficient(self) -> float:
        """
        Calculate Consistency Coefficient (CC) - correlation between
        question difficulty and cognitive process level

        Returns:
            Pearson correlation coefficient or None if calculation fails
        """
        if not self.classified_questions:
            return None

        # Extract difficulty and cognitive process level pairs
        pairs = []
        for q in self.classified_questions:
            cognitive = q["classification"]["cognitive_process"]
            if cognitive in COGNITIVE_PROCESS:
                pairs.append((q["difficulty"], COGNITIVE_PROCESS[cognitive]))

        # Calculate Pearson correlation if enough data points
        if len(pairs) >= 3:
            difficulties, cognitive_levels = zip(*pairs)
            correlation, _ = pearsonr(difficulties, cognitive_levels)
            return correlation
        else:
            return None

    def visualize_distribution(self, output_dir: str = "."):
        """
        Create visualizations of the question distribution

        Args:
            output_dir: Directory to save visualization files
        """
        if not self.classified_questions:
            print("No classified questions available for visualization.")
            return

        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)

        # Get distribution data
        analysis = self.analyze_distribution()

        # Create figure for cognitive process distribution
        plt.figure(figsize=(10, 6))

        # Get actual and target distributions
        actual_dist = {
            k: analysis["cognitive_percentages"].get(k, 0) for k in COGNITIVE_PROCESS.keys()
        }
        target_dist = TARGET_DISTRIBUTION

        # Create bar chart
        categories = list(COGNITIVE_PROCESS.keys())
        x = np.arange(len(categories))
        width = 0.35

        fig, ax = plt.subplots(figsize=(12, 7))
        ax.bar(
            x - width / 2, [actual_dist.get(cat, 0) for cat in categories], width, label="Actual"
        )
        ax.bar(
            x + width / 2, [target_dist.get(cat, 0) for cat in categories], width, label="Target"
        )

        # Add labels and title
        ax.set_xlabel("Cognitive Process Dimension")
        ax.set_ylabel("Percentage")
        ax.set_title("Distribution of Questions by Cognitive Process")
        ax.set_xticks(x)
        ax.set_xticklabels(categories)
        ax.legend()

        # Rotate x-axis labels for better readability
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")

        # Add value labels on bars
        for i, v in enumerate([actual_dist.get(cat, 0) for cat in categories]):
            ax.text(i - width / 2, v + 0.02, f"{v:.1%}", ha="center")

        for i, v in enumerate([target_dist.get(cat, 0) for cat in categories]):
            ax.text(i + width / 2, v + 0.02, f"{v:.1%}", ha="center")

        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, "cognitive_distribution.png"))

        # Create pie chart for LOTS vs HOTS
        plt.figure(figsize=(8, 8))
        labels = ["LOTS", "HOTS"]
        sizes = [analysis["lots_percentage"], analysis["hots_percentage"]]
        explode = (0.1, 0)  # explode LOTS slice

        fig1, ax1 = plt.subplots(figsize=(8, 8))
        ax1.pie(
            sizes, explode=explode, labels=labels, autopct="%1.1f%%", shadow=True, startangle=90
        )
        ax1.axis("equal")  # Equal aspect ratio ensures that pie is drawn as a circle
        ax1.set_title("Distribution of Lower Order vs Higher Order Thinking Skills")
        plt.savefig(os.path.join(output_dir, "lots_hots_distribution.png"))

        # Create radar chart for quality metrics
        metrics = analysis["quality_metrics"]

        # Normalize metrics to 0-1 scale for radar chart
        normalized_metrics = {
            "Coverage Score": metrics["coverage_score"] / 100,
            "Shannon Diversity": min(
                metrics["shannon_diversity_index"] / 2, 1
            ),  # Assuming max SDI around 2
            "Consistency Coefficient": (
                (metrics["consistency_coefficient"] + 1) / 2
                if metrics["consistency_coefficient"] is not None
                else 0.5
            ),
        }

        # Number of variables
        categories = list(normalized_metrics.keys())
        N = len(categories)

        # Create angle for each variable
        angles = [n / float(N) * 2 * np.pi for n in range(N)]
        angles += angles[:1]  # Close the loop

        # Create radar chart
        fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))

        # Add the first line (actual metrics)
        values = list(normalized_metrics.values())
        values += values[:1]  # Close the loop
        ax.plot(angles, values, linewidth=1, linestyle="solid", label="Actual")
        ax.fill(angles, values, alpha=0.1)

        # Add a second line (target metrics)
        target_values = [0.9, 0.75, 0.7]  # Target values for metrics
        target_values += target_values[:1]  # Close the loop
        ax.plot(angles, target_values, linewidth=1, linestyle="solid", label="Target")
        ax.fill(angles, target_values, alpha=0.1)

        # Set category labels
        plt.xticks(angles[:-1], categories)

        # Add legend
        plt.legend(loc="upper right")

        plt.title("Quality Metrics Assessment")
        plt.savefig(os.path.join(output_dir, "quality_metrics_radar.png"))

        # Close all figures
        plt.close("all")

        print(f"Visualization files saved to {output_dir}")

    def save_classified_questions(self, output_file: str):
        """
        Save classified questions to a JSON file

        Args:
            output_file: Path to output JSON file
        """
        if not self.classified_questions:
            print("No classified questions available to save.")
            return

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(self.classified_questions, f, indent=2)

        print(f"Classified questions saved to {output_file}")

    def generate_report(self, output_file: str):
        """
        Generate a comprehensive report on question quality

        Args:
            output_file: Path to output report file (markdown format)
        """
        if not self.classified_questions:
            print("No classified questions available for reporting.")
            return

        # Get analysis data
        analysis = self.analyze_distribution()

        # Format the consistency coefficient value with proper condition handling
        cc_value = analysis["quality_metrics"]["consistency_coefficient"]
        if cc_value is not None:
            cc_formatted = f"{cc_value:.2f}"
        else:
            cc_formatted = "N/A"

        # Prepare report content
        report = f"""# Question Quality Analysis Report

## Summary

- **Total Questions Analyzed**: {len(self.classified_questions)}
- **Coverage Score**: {analysis["quality_metrics"]["coverage_score"]:.2f}%
- **Shannon Diversity Index**: {analysis["quality_metrics"]["shannon_diversity_index"]:.2f}
- **Consistency Coefficient**: {cc_formatted}

## Cognitive Process Distribution

| Cognitive Process | Count | Actual % | Target % | Difference |
|------------------|-------|----------|----------|------------|
"""

        # Add rows for each cognitive process
        for category in COGNITIVE_PROCESS.keys():
            actual = analysis["cognitive_percentages"].get(category, 0)
            target = TARGET_DISTRIBUTION.get(category, 0)
            diff = actual - target

            report += f"| {category.capitalize()} | {analysis['cognitive_counts'].get(category, 0)} | {actual:.1%} | {target:.1%} | {diff:+.1%} |\n"

        # Add LOTS vs HOTS section
        report += f"""
## Higher Order vs Lower Order Thinking Skills

| Category | Actual % | Target % | Difference |
|----------|----------|----------|------------|
| LOTS (Remember, Understand, Apply) | {analysis["lots_percentage"]:.1%} | {TARGET_LOTS_RATIO:.1%} | {analysis["lots_percentage"]-TARGET_LOTS_RATIO:+.1%} |
| HOTS (Analyze, Evaluate, Create) | {analysis["hots_percentage"]:.1%} | {TARGET_HOTS_RATIO:.1%} | {analysis["hots_percentage"]-TARGET_HOTS_RATIO:+.1%} |

## Knowledge Dimension Distribution

| Knowledge Dimension | Count | Percentage |
|---------------------|-------|------------|
"""

        # Add rows for each knowledge dimension
        for dimension in KNOWLEDGE_DIMENSIONS:
            count = analysis["knowledge_counts"].get(dimension, 0)
            percentage = analysis["knowledge_percentages"].get(dimension, 0)

            report += f"| {dimension.capitalize()} | {count} | {percentage:.1%} |\n"

        # Format metrics with proper condition handling for the assessment section
        cc_value = analysis["quality_metrics"]["consistency_coefficient"]
        cc_met = "✅ Met" if cc_value is not None and cc_value >= 0.7 else "❌ Not Met"

        # Add quality metrics assessment
        report += f"""
## Quality Metrics Assessment

| Metric | Value | Target | Assessment |
|--------|-------|--------|------------|
| Coverage Score | {analysis["quality_metrics"]["coverage_score"]:.2f}% | ≥90% | {"✅ Met" if analysis["quality_metrics"]["coverage_score"] >= 90 else "❌ Not Met"} |
| Shannon Diversity Index | {analysis["quality_metrics"]["shannon_diversity_index"]:.2f} | ≥1.5 | {"✅ Met" if analysis["quality_metrics"]["shannon_diversity_index"] >= 1.5 else "❌ Not Met"} |
| Consistency Coefficient | {cc_formatted} | ≥0.7 | {cc_met} |

## Recommendations

"""

        # Add recommendations based on analysis
        if analysis["quality_metrics"]["coverage_score"] < 90:
            missing_categories = [
                cat for cat in COGNITIVE_PROCESS.keys() if cat not in analysis["cognitive_counts"]
            ]
            report += f"- **Improve Coverage**: Add questions from missing cognitive categories: {', '.join(missing_categories)}\n"

        if analysis["quality_metrics"]["shannon_diversity_index"] < 1.5:
            report += "- **Improve Diversity**: Balance question distribution across cognitive categories\n"

        if cc_value is None or (cc_value is not None and cc_value < 0.7):
            report += "- **Improve Consistency**: Align question difficulty with cognitive process levels\n"

        # Add recommendations for categories with large discrepancies
        for category in COGNITIVE_PROCESS.keys():
            actual = analysis["cognitive_percentages"].get(category, 0)
            target = TARGET_DISTRIBUTION.get(category, 0)
            diff = actual - target

            if abs(diff) > 0.1:  # More than 10% difference
                if diff > 0:
                    report += f"- **Reduce {category.capitalize()} Questions**: Current proportion ({actual:.1%}) is significantly higher than target ({target:.1%})\n"
                else:
                    report += f"- **Add {category.capitalize()} Questions**: Current proportion ({actual:.1%}) is significantly lower than target ({target:.1%})\n"

        # Write report to file
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"Report saved to {output_file}")


def main():
    """Main function to run the question experiment"""
    parser = argparse.ArgumentParser(description="Analyze exam questions using Bloom's Taxonomy")
    parser.add_argument(
        "--input",
        "-i",
        default="data/exam_questions.json",
        help="Path to the JSON file containing exam questions",
    )
    parser.add_argument(
        "--output-dir", "-o", default="output", help="Directory to save output files"
    )
    parser.add_argument(
        "--api-key",
        "-k",
        help="OpenAI API key (optional, will use environment variable if not provided)",
    )
    parser.add_argument(
        "--classify", "-c", action="store_true", help="Classify questions using OpenAI API"
    )
    parser.add_argument(
        "--report", "-r", action="store_true", help="Generate a report of question quality"
    )
    parser.add_argument(
        "--visualize",
        "-v",
        action="store_true",
        help="Create visualizations of question distribution",
    )

    args = parser.parse_args()

    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)

    # Initialize question analyzer
    analyzer = QuestionAnalyzer(args.input, args.api_key)

    # Classify questions if requested
    if args.classify:
        analyzer.classify_all_questions()
        analyzer.save_classified_questions(
            os.path.join(args.output_dir, "classified_questions.json")
        )
    else:
        # Try to load previously classified questions
        try:
            with open(os.path.join(args.output_dir, "classified_questions.json"), "r") as f:
                analyzer.classified_questions = json.load(f)
            print(f"Loaded {len(analyzer.classified_questions)} previously classified questions")
        except FileNotFoundError:
            print("No previously classified questions found. Use --classify to classify questions.")

    # Generate report if requested
    if args.report and analyzer.classified_questions:
        analyzer.generate_report(os.path.join(args.output_dir, "question_quality_report.md"))

    # Create visualizations if requested
    if args.visualize and analyzer.classified_questions:
        analyzer.visualize_distribution(args.output_dir)


if __name__ == "__main__":
    main()
