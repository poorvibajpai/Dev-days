import os
import sys
import tempfile
import click
from git import Repo
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

# Initialize rich console
console = Console()

# Common directories and files to ignore
IGNORE_DIRS = {'.git', 'node_modules', 'venv', 'env', '__pycache__', 'dist', 'build', '.idea', '.vscode'}
IGNORE_EXTS = {'.pyc', '.pyo', '.so', '.dll', '.exe', '.bin', '.pdf', '.png', '.jpg', '.jpeg', '.gif', '.mp4', '.zip', '.tar', '.gz'}
MAX_FILE_SIZE = 50 * 1024  # 50KB limit per file to avoid huge context

def is_text_file(filepath):
    try:
        with open(filepath, 'tr') as check_file:
            check_file.read(1024)
            return True
    except:
        return False

def extract_codebase(path: str) -> str:
    """Reads the repository and extracts the file tree and contents."""
    tree = []
    contents = []
    
    root_path = Path(path)
    
    for root, dirs, files in os.walk(root_path):
        # Modify dirs in-place to skip ignored directories
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith('.')]
        
        rel_root = Path(root).relative_to(root_path)
        if str(rel_root) == '.':
            tree.append('/')
        else:
            tree.append(f"/{rel_root}/")
            
        for file in files:
            file_path = Path(root) / file
            
            # Skip hidden files and ignored extensions
            if file.startswith('.') or file_path.suffix.lower() in IGNORE_EXTS:
                continue
                
            tree.append(f"  {file}")
            
            # Check file size
            try:
                if file_path.stat().st_size > MAX_FILE_SIZE:
                    contents.append(f"\n--- {rel_root / file} [SKIPPED: File too large] ---\n")
                    continue
            except OSError:
                continue
                
            if is_text_file(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        file_content = f.read()
                        contents.append(f"\n--- {rel_root / file} ---\n{file_content}\n")
                except UnicodeDecodeError:
                    contents.append(f"\n--- {rel_root / file} [SKIPPED: Not text] ---\n")
                    
    context = "DIRECTORY STRUCTURE:\n" + "\n".join(tree) + "\n\n"
    context += "FILE CONTENTS:\n" + "".join(contents)
    
    # Simple token truncation to avoid blowing up context window entirely
    # OpenAI context windows are large, but we'll limit character count to ~100k chars for safety
    if len(context) > 300000:
        context = context[:300000] + "\n\n... [TRUNCATED DUE TO SIZE] ..."
        
    return context

def roast_and_analyze(codebase: str, mock: bool = False) -> str:
    """Uses LLM to roast the codebase and provide market research."""
    if mock:
        return """
### 1. The Roast 🔥
- **Monolithic Madness**: Your `roaster.py` is doing everything from cloning repos to parsing files to calling OpenAI. Ever heard of the Single Responsibility Principle, or is that too enterprise for you?
- **Error Handling? What's That?**: Catching generic `Exception` at the bottom of the script? Bold move. Hope you like debugging silently failing edge cases in production.
- **Context Window Roulette**: Truncating the context to exactly 300,000 characters and slapping "TRUNCATED" at the end is like trying to fit a watermelon into a blender by just chopping it in half and hoping the lid stays on.
- **Dependency Overkill**: You imported `tempfile`, `sys`, and `os`, but you're also using `pathlib.Path`. Pick a lane, file system API! 
- **Security by "Please Don't"**: Relying on `.env.example` and hoping users don't accidentally commit their `.env` file because you forgot to add a `.gitignore` to your own project. Ironic for a repo analyzer.

### 2. Solutions 🛠️
- **Refactor into Modules**: Split the code into `cli.py` (Click interface), `extractor.py` (Git and file system logic), and `llm.py` (OpenAI integration).
- **Better Context Management**: Instead of a hard character cutoff, use `tiktoken` to actually count tokens and prioritize smaller/more relevant files.
- **Add a `.gitignore`**: Seriously, add `.env` to a `.gitignore` right now before someone leaks their OpenAI API key.
- **Graceful Error Handling**: Catch specific exceptions (e.g., `git.exc.GitCommandError`, `openai.APIError`) and provide actionable error messages to the user.

### 3. Market Research 📊
Are you reinventing the wheel? **Yes.**
- **GitHub Copilot / Cursor**: Already analyze codebases and provide refactoring suggestions contextually.
- **CodeRabbit / Sweep.dev**: Automated PR reviewers that essentially "roast" (and fix) your code on every commit.
- **Aider**: A CLI tool that pairs with LLMs to read your repo and make edits.

*Verdict*: It's a fun weekend project, but don't quit your day job to launch this as a SaaS.
"""
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    system_prompt = (
        "You are an elite, brutally honest software architect and product strategist. "
        "Your task is to analyze a codebase provided by the user.\n\n"
        "1. Roast the repository in 5-8 bullet points. Be funny, ruthless, but accurate based on the code provided.\n"
        "2. Give concrete solutions and architectural improvements to fix the roasted points.\n"
        "3. Provide market research: what existing products, tools, or libraries already do what this repo is trying to do? Are they reinventing the wheel?"
    )
    
    user_prompt = f"Here is the codebase:\n\n{codebase}"
    
    response = client.chat.completions.create(
        model="gpt-4-turbo-preview",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.7,
        max_tokens=2000
    )
    
    return response.choices[0].message.content

@click.command()
@click.argument('repo_path_or_url')
@click.option('--mock', is_flag=True, help='Run in mock mode without calling OpenAI API.')
def main(repo_path_or_url, mock):
    """
    Reads a git repository (local path or URL) and roasts it.
    """
    load_dotenv()
    if not mock and not os.getenv("OPENAI_API_KEY"):
        console.print("[red]Error: OPENAI_API_KEY environment variable is not set. Please set it in .env file or export it.[/red]")
        sys.exit(1)
        
    temp_dir = None
    target_path = repo_path_or_url
    
    try:
        # Check if it's a URL
        if repo_path_or_url.startswith(('http://', 'https://', 'git@')):
            console.print(f"[bold blue]Cloning repository {repo_path_or_url}...[/bold blue]")
            temp_dir = tempfile.TemporaryDirectory()
            Repo.clone_from(repo_path_or_url, temp_dir.name)
            target_path = temp_dir.name
        elif not os.path.exists(repo_path_or_url):
            console.print(f"[red]Error: Path {repo_path_or_url} does not exist.[/red]")
            sys.exit(1)
            
        console.print("[bold yellow]Extracting codebase context...[/bold yellow]")
        codebase_context = extract_codebase(target_path)
        
        console.print("[bold magenta]Sending to the roasting chamber (LLM analysis)...[/bold magenta]")
        result = roast_and_analyze(codebase_context, mock=mock)
        
        console.print(Panel.fit("🔥 ROAST & ANALYSIS COMPLETE 🔥", style="bold red"))
        console.print(Markdown(result))
        
    except Exception as e:
        console.print(f"[red]An error occurred: {str(e)}[/red]")
        
    finally:
        if temp_dir:
            temp_dir.cleanup()

if __name__ == '__main__':
    main()
