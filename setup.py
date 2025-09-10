from setuptools import find_packages, setup

with open('README.md', 'r', encoding='utf-8') as fh:
    long_description = fh.read()

setup(
    name='news-agent',
    version='0.1.0',
    author='Sadanand Singh',
    author_email='sadanand.singh@reckoning.dev',
    description='Agentic AI for News ',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/sadanand-singh/news-agent',
    packages=find_packages(),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
    ],
    python_requires='>=3.11',
    install_requires=[
        'langchain-core',
    ],
    extras_require={
        'openai': ['langchain-openai'],
        'anthropic': ['langchain-anthropic'],
        'google': ['langchain-google-genai'],
        'ollama': ['langchain-ollama'],
        'all': [
            'langchain-openai',
            'langchain-anthropic',
            'langchain-google-genai',
            'langchain-ollama',
        ],
    },
)
