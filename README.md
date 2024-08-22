# ffufai

ffufai is an AI-powered wrapper for the popular web fuzzer ffuf. It automatically suggests file extensions for fuzzing based on the target URL and its headers, using either OpenAI's GPT or Anthropic's Claude AI models.

## Features

- Seamlessly integrates with ffuf
- Automatically suggests relevant file extensions for fuzzing
- Supports both OpenAI and Anthropic AI models
- Passes through all ffuf parameters

## Prerequisites

- Python 3.6+
- ffuf (installed and accessible in your PATH)
- An OpenAI API key or Anthropic API key

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/ffufai.git
   cd ffufai
   ```

2. Install the required Python packages:
   ```
   pip install requests openai anthropic
   ```

3. Make the script executable:
   ```
   chmod +x ffufai.py
   ```

4. (Optional) To use ffufai from anywhere, add it to your PATH. You can do this by adding the following line to your `~/.bashrc` or `~/.zshrc` file:
   ```
   export PATH="/path/to/ffufai/directory:$PATH"
   ```
   Replace "/path/to/ffufai/directory" with the actual path where you cloned the repository.

5. Set up your API key as an environment variable:
   For OpenAI:
   ```
   export OPENAI_API_KEY='your-api-key-here'
   ```
   Or for Anthropic:
   ```
   export ANTHROPIC_API_KEY='your-api-key-here'
   ```

   You can add these lines to your `~/.bashrc` or `~/.zshrc` file to make them permanent.

## Usage

Use ffufai just like you would use ffuf, but replace `ffuf` with `ffufai.py` (or just `ffufai` if you've added it to your PATH):

```
ffufai.py -u https://example.com/FUZZ -w /path/to/wordlist.txt
```

ffufai will automatically suggest extensions based on the URL and add them to the ffuf command.

## Notes

- ffufai requires the `FUZZ` keyword to be used and to be at the end of the URL path for accurate extension suggestion. It will warn you if this is not the case.
- All ffuf parameters are passed through to ffuf, so you can use any ffuf option with ffufai.
- If both OpenAI and Anthropic API keys are set, ffufai will prefer the OpenAI key.

## Troubleshooting

- If you encounter a "command not found" error, make sure ffufai.py is in your PATH or use the full path to the script.
- If you get an API key error, ensure you've correctly set up your OPENAI_API_KEY or ANTHROPIC_API_KEY environment variable.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.