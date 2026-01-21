<div align="center">

<img src="https://github.com/user-attachments/assets/1f9ce2d7-8f9d-4746-bad4-acfccad74900" alt="ffufai_logo" width="400">

# `ffufai`

![GitHub top language](https://img.shields.io/github/languages/top/jthack/ffufai)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

<p class="align center">

ffufai is an AI-powered wrapper for the popular web fuzzer ffuf. It automatically suggests file extensions for fuzzing based on the target URL and its headers, using either OpenAI's GPT or Anthropic's Claude AI models and Free Hugging Face models on local.

</p>

</div>

## Features
<img width="600  " alt="image" src="https://github.com/user-attachments/assets/0384d4f0-3a07-48d9-9805-ea1e76b6b693">

- Seamlessly integrates with ffuf
- Automatically suggests relevant file extensions for fuzzing
- Supports both OpenAI, Anthropic AI models and Free Hugging Face AI models 
- Passes through all ffuf parameters

## Prerequisites

- Python 3.6+
- ffuf (installed and accessible in your PATH)
- An OpenAI API key | Anthropic API key | Gemini API key | Free Hugging Face API key 

## Installation

1. Clone this repository :
   ```
   git clone https://github.com/ikajakam/ffufai.git
   cd ffufai
   ```

2. Install the required Python packages :
   ```
   pip install requests openai anthropic
   ```

3. To load and run `Qwen/Qwen2.5-1.5B-Instruct` model locally via Hugging Face :
	```
	pip install transformers torch accelerate
	```
	```
	poetry add accelerate
	```
- Models are cached in `~/.cache/huggingface`

4. To use ffufai globally from terminal, create a symbolic link in a directory that's in your PATH.
   ```
   sudo ln -s /full/path/to/ffufai.py /usr/local/bin/ffufai
   ```
   Replace "/full/path/to/ffufai.py" with the actual full path to where you cloned the repository.

6. Set up your API key as an environment variable :

   OpenAI :
   ```
   export OPENAI_API_KEY='your-api-key-here'
   ```
   Anthropic :
   ```
   export ANTHROPIC_API_KEY='your-api-key-here'
   ```
   Gemini :
   ```
   export GEMINI_API_KEY="your-api-key-here"
   ```
   Hugging Face :
   ```
   export HUGGINGFACE_API_KEY=your-api-key-here        ## no '' 
   ```
   
   You can add these lines to your `~/.bashrc` or `~/.zshrc` file to make them permanent and reload your `~/.bashrc` or `~/.zshrc`

## Usage

Use ffufai just like you would use ffuf, but replace `ffuf` with `python3 ffufai.py` (or just `ffufai` if you've created the symbolic link) :

```
python3 ffufai.py -u https://example.com/FUZZ -w /path/to/wordlist.txt
```

Or if you've created the symbolic link :

```
ffufai -u https://example.com/FUZZ -w /path/to/wordlist.txt
```

ffufai will automatically suggest extensions based on the URL and add them to the ffuf command.


## Parameters

ffufai accepts all the parameters that ffuf does, plus a few additional ones:

- `--ffuf-path`: Specifies the path to the ffuf executable. Default is 'ffuf'.  
  Example: `ffufai --ffuf-path /usr/local/bin/ffuf -u https://example.com/FUZZ -w wordlist.txt`

- `--max-extensions`: Sets the maximum number of extensions to suggest. Default is 4.  
  Example: `ffufai --max-extensions 6 -u https://example.com/FUZZ -w wordlist.txt`

- `-u`: Specifies the target URL. This parameter is required and should include the FUZZ keyword.  
  Example: `ffufai -u https://example.com/FUZZ -w wordlist.txt`

- `-w`: Specifies the wordlist to use for fuzzing. This is a standard ffuf parameter.  
  Example: `ffufai -u https://example.com/FUZZ -w /path/to/wordlist.txt`

All other ffuf parameters can be used as normal. For a full list of ffuf parameters, refer to the ffuf documentation.

## Notes

- ffufai requires the FUZZ keyword to be at the end of the URL path for accurate extension suggestion. It will warn you if this is not the case.
- All ffuf parameters are passed through to ffuf, so you can use any ffuf option with ffufai.



## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

