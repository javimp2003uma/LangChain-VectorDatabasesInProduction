import os
import requests
from bs4 import BeautifulSoup
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import DeepLake
from langchain.text_splitter import CharacterTextSplitter
from langchain.document_loaders import TextLoader
import re

def load_api_keys(filepath):
    api_keys = {}
    with open(filepath, 'r') as file:
        for line in file:
            key_name, key_value = line.strip().split(':', 1)
            api_keys[key_name.strip()] = key_value.strip()
    return api_keys

# Load API keys from the file
api_keys = load_api_keys('APIkeys.txt')
os.environ["OPENAI_API_KEY"] = api_keys.get('openai', '')
os.environ['ELEVEN_API_KEY'] = api_keys.get('elevenlabs', '')
os.environ['ACTIVELOOP_TOKEN'] = api_keys.get('activeloop', '')

# Get the dataset path from the environment variable
my_activeloop_org_id = "your_activeloop_username"
my_activeloop_dataset_name = "LangchainAndDeeplakeVoiceAssistant"
dataset_path= f'hub://{my_activeloop_org_id}/{my_activeloop_dataset_name}'

embeddings =  OpenAIEmbeddings(model="text-embedding-ada-002")

def get_documentation_urls():
    # List of full URLs for History topics
    return [
        'https://en.wikipedia.org/wiki/Pel%C3%A9',
        'https://en.wikipedia.org/wiki/Diego_Maradona',
        'https://en.wikipedia.org/wiki/Lionel_Messi'
        # 'https://en.wikipedia.org/wiki/Cristiano_Ronaldo',
        # 'https://en.wikipedia.org/wiki/Johan_Cruyff',
        # 'https://en.wikipedia.org/wiki/Zinedine_Zidane',
        # 'https://en.wikipedia.org/wiki/Michel_Platini',
        # 'https://en.wikipedia.org/wiki/Franz_Beckenbauer'
    ]

def construct_full_url(base_url, relative_url):
    # Construct the full URL by appending the relative URL to the base URL
    return base_url + relative_url

def scrape_page_content(url):
    # Send a GET request to the URL and parse the HTML response using BeautifulSoup
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    # Extract the desired content from the page (in this case, the body text)
    text=soup.body.text.strip()
    # Remove non-ASCII characters
    text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\xff]', '', text)
    # Remove extra whitespace and newlines
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def scrape_all_content(full_urls, filename):
    # Loop through the list of URLs, scrape content and add it to the content list
    content = []
    for full_url in full_urls:
        scraped_content = scrape_page_content(full_url)
        content.append(scraped_content.rstrip('\n'))

    # Write the scraped content to a file
    with open(filename, 'w', encoding='utf-8') as file:
        for item in content:
            file.write("%s\n" % item)
    
    return content

# Define a function to load documents from a file
def load_docs(root_dir,filename):
    # Create an empty list to hold the documents
    docs = []
    try:
        # Load the file using the TextLoader class and UTF-8 encoding
        loader = TextLoader(os.path.join(
            root_dir, filename), encoding='utf-8')
        # Split the loaded file into separate documents and add them to the list of documents
        docs.extend(loader.load_and_split())
    except Exception as e:
        # If an error occurs during loading, ignore it and return an empty list of documents
        pass
    # Return the list of documents
    return docs
  
def split_docs(docs):
    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
    return text_splitter.split_documents(docs)

def batch_texts(texts, batch_size = 100):
    for i in range(0, len(texts), batch_size):
        yield texts[i:i + batch_size]

def process_batches(texts):
    for batch in batch_texts(texts):
        # Assuming `db.add_documents` can handle a batch
        db.add_documents(batch)

    
# Set the name of the file to which the scraped content will be saved
filename = 'content.txt'
# Set the root directory where the content file will be saved
root_dir = os.getcwd()
all_urls = get_documentation_urls()
# Scrape all the content from the relative URLs and save it to the content file
content = scrape_all_content(all_urls,filename)
# Load the content from the file
docs = load_docs(root_dir,filename)
# Split the content into individual documents
texts = split_docs(docs)
# Create a DeepLake database with the given dataset path and embedding function
db = DeepLake(dataset_path=dataset_path, embedding_function=embeddings)
# Add the individual documents to the database
#db.add_documents(texts)
process_batches(texts)
# Clean up by deleting the content file
os.remove(filename)