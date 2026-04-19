# Repo Roaster 🔥

An automation tool that reads a git repository, brutally roasts it in 5-8 points, provides actionable solutions, and gives you market research on whether you are just reinventing the wheel.

## Features

- **Repo Reading**: Clones any public git repository or reads a local directory.
- **Smart Extraction**: Automatically ignores binary files, large files, and common noise (like `node_modules` and `.git`).
- **AI Roasting**: Uses OpenAI's GPT-4 to analyze your codebase, roast your architectural choices, and provide a 5-8 point critique.
- **Market Research**: Analyzes the core idea behind the repository and tells you what existing products or libraries already do it better.

## Prerequisites

- Python 3.8+
- An OpenAI API Key

## Installation

1. Clone or download this project.
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy the `.env.example` file to `.env` and add your OpenAI API Key:
   ```bash
   cp .env.example .env
   # Edit .env and set your OPENAI_API_KEY
   ```

## Usage

You can point the roaster at a local directory or a public Git URL:

```bash
# Roast a public GitHub repository
python roaster.py https://github.com/username/repository.git

# Roast a local project
python roaster.py /path/to/your/local/project
```

## Example Output

1. **Cloning repository...**
2. **Extracting codebase context...**
3. **Sending to the roasting chamber (LLM analysis)...**
4. **🔥 ROAST & ANALYSIS COMPLETE 🔥**
   - **Roast**: "Your `utils.py` is a 2,000-line dumping ground. It's not a utility file, it's a landfill..."
   - **Solutions**: "Split `utils.py` into domain-specific modules..."
   - **Market Research**: "You've built a custom state management library that is essentially a worse version of Redux..."
