import json
from mimetypes import guess_type
import tiktoken
from openai import AzureOpenAI
from src.client_models.gpt4_clients import BaseGPTClient



pdf_prompts = [
    "In a hearing meeting of a municipality's Land Use, Zoning, Urban development related meetings, there would be multiple issues adressed. The minutes of the meetings are recorded. The minutes could be summarizing appeals done in the meeting, their outcomes of approvals or denials, or some other initiatives taken by the city. I need you to process the following text from the minutes of the meeting and return me a structured data with rows corresponding to each item discussed in the meeting. ",
    "I need you to list out every address that's mentioned in this text file, along with the date, the full name (or business name) of who's involved, any changes that were proposed, if those changes were approved, and a brief summary of what was discussed.",
    "Please remember your response as a json array where each object has the specified keys. The response should look like [{index:'index of the address', address: 'Exact Address Found', city: 'City', state: '2 or 3 letter State code', zipcode: 'Zip code of the address found if available, otherwise use your knowledge to get zip code of the given city and state', party: 'involved party name',status: 'APPROVED|DENIED|PENDING', remarks: 'any remarks related to the approval status, if applicable', summary: 'summary of the proceeding corresponding to this address'}].", 
    "Finally, return a final JSON object that has both the metadata of the keys in each oibject and the entire response. It looks like this : `{columns: [{title: 'Index', dataIndex: 'index', key:'1'}, {title: 'Address', dataIndex: 'address', key:'2'}... and so on ], response: YOUR_JSON_RESPONSE}`",
    "List as much information as possible obtained in the given text. Remember each object of the array you return corresponds to a specific address.",
    "Please respond in a strictly json object. Do not include any explanation.",
]

chat_pdf_prompts = [
    "In a hearing meeting of a municipality's Land Use, Zoning, Urban development related meetings, there would be multiple issues adressed. The minutes of the meetings are recorded. The minutes could be summarizing appeals done in the meeting, their outcomes of approvals or denials, or some other initiatives taken by the city. I need you to process the following text from the minutes of the meeting and return me responses corresponding to each item discussed in the meeting.",
]

json_message = "Please respond in a strictly json object. Do not include any explanation."

class GPT4OClient(BaseGPTClient):
    def __init__(self, api_base: str, api_key: str, api_version: str, deployment_name: str) -> None:
        super().__init__()
        self._client = AzureOpenAI(
            api_key=api_key,
            api_version=api_version,
            base_url=f"{api_base}openai/deployments/{deployment_name}",
        )
        self._deployment_name = deployment_name

    @property
    def client(self):
        return self._client
   
    @property
    def deployment_name(self):
        return self._deployment_name

    def chat_completion(self, messages, max_tokens, response_format):
        try :
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=messages,
                max_tokens=max_tokens,
                response_format=response_format
            )
            return response
        except Exception as e:
            # if e["error"] is not None:
            #     print("Exception from GPT", e["error"]["message"], e["error"]["param"])
            # else :
            print("Exception from GPT", e)
            raise

    def get_pdf_data(self, text) -> str:
        messages=[
            {
                "role": "system",
                "content": "You are a Data Analyst working a city municipality. The municipality records minutes of its meetings, that correspond to many different departments such as Planning Commission Zoning Department, Land Use, Community Development,Urban Planning etc",
            },
            {
                "role": "user",
                "content": ' '.join(pdf_prompts),
            }, 
            {
                "role": "user",
                "content": text,
            },           
        ]
        # print('fetching tokjens')
        # num_tokens = self.num_tokens_from_messages(messages)
  
        # print(messages)   
        try:
            response = self.chat_completion(
                messages=messages,
                max_tokens=10000,
                response_format={"type": "json_object"}
            )
            print(f'Tokens : {response.usage.prompt_tokens}')
        except Exception as e:
            raise Exception("Error fetching response from GPT") from e
         
        description = response.choices[0].message.content
        if description is None or description.strip() == "":
            description = "I apologize, but I am having difficulty providing a detailed description of this image. The image quality or content may be challenging for me to interpret accurately. Please provide additional guidance or consider uploading a clearer image if possible."
        response = {
            "usage": response.usage,
            "text" : text,
            "response" : description.strip() 
        }
        return response 
    
    def num_tokens_content(self, content, model="gpt-4o-mini"):
        """Return the number of tokens used by a list of messages."""
        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            print("Warning: model not found. Using cl100k_base encoding.")
            encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(content))

    # find out if the first message_ was intended or can be removed
    def converse(self, text, question, json_response) -> str:
        """
        Converse with the GPT-4O model using the provided text and question.

        Args:
            text (str): The text to analyze.
            question (str): The question to ask.
            json_response (bool): Whether to format the response as JSON.

        Returns:
            dict: The response from the GPT-4O model.
        """
        messages_ =[
            {
                "role": "system",
                "content": "You are a Data Analyst working a city municipality. The municipality records minutes of its meetings, that correspond to many different departments such as Planning Commission Zoning Department, Land Use, Community Development,Urban Planning etc",
            },
            {
                "role": "user",
                "content": f"{' '.join(chat_pdf_prompts)} {json_message if json_response else ''}",
            }, 
            {
                "role": "user",
                "content": text,
            }, 
            {
                "role": "user",
                "content": question,
            },            
        ]        
        messages = [
            {
            "role": "system",
            "content": "You are an AI assistant analyzing transcripts from city municipality meetings. These transcripts cover various departments such as Planning Commission, Zoning Department, Land Use, Community Development, and Urban Planning. Your task is to understand the content, identify people who spoke and understand what they said, regarding key points, identify important decisions, and answer questions about the meeting content."
            },
            {
            "role": "user",
            "content": f"Here is a transcript from a recent municipality meeting:\n\n{text}\n\nPlease answer the following question."
            },
        ]
        if json_response:
            messages.append({
                "role": "user",
                "content": "Make sure your response is strictly a json object that looks like {'data': []}and that I can display in React antd Table component!",
            })
            messages.append({
                "role": "user",
                "content": question,
            }
        )
        try:
            if json_response :
                response = self.chat_completion(
                    messages=messages,
                    max_tokens=10000,
                    response_format={"type": "json_object"}
                )
            else:
                response = self.chat_completion(
                    messages=messages,
                    max_tokens=10000,
                    response_format={"type": "text"}
                )                
            print(f'Tokens : {response.usage.prompt_tokens}')
        except Exception as e:
            raise Exception("Error fetching response from GPT") from e
         
        description = response.choices[0].message.content
        if description is None or description.strip() == "":
            description = "I apologize, but I am having difficulty providing a detailed description of this image. The image quality or content may be challenging for me to interpret accurately. Please provide additional guidance or consider uploading a clearer image if possible."
        response = {
            "usage": response.usage,
            "response" : description.strip() 
        }
        return response 