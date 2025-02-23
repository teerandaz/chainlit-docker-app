import chainlit as cl
import pandas as pd
import google.generativeai as genai
import io
from io import StringIO
import sys

# Configure the API key
genai.configure(api_key="AIzaSyCvxNV0TvG0C28u6HNlHtNc_XOHvGSH8MA")

model = genai.GenerativeModel('gemini-1.5-flash')
global_df = None

def capture_output(code, global_df):
    # Create string buffer to capture output
    old_stdout = sys.stdout
    redirected_output = StringIO()
    sys.stdout = redirected_output
    
    # Create namespace for execution
    local_vars = {}
    global_vars = {"global_df": global_df.copy(), "pd": pd}
    
    try:
        # Execute the code
        exec(code, global_vars, local_vars)
        sys.stdout = old_stdout
        
        # Get printed output
        printed_output = redirected_output.getvalue()
        
        # Get returned result if any
        result = local_vars.get('result', None)
        
        return printed_output, result
    except Exception as e:
        sys.stdout = old_stdout
        raise e
    finally:
        sys.stdout = old_stdout

def handle_query(df, user_query):
    context = f"""
    You are a helpful assistant capable of handling both data analysis and general knowledge questions. 

    **Important Instructions:**
    1. First determine if the user's question is about the uploaded data (analysis required) or a general question.
    2. For data-related questions:
       - The DataFrame has {len(df)} rows and columns: {', '.join(df.columns)}
       - Provide Python code if analysis is needed, storing results in a 'result' variable
       - Include print statements for key insights
       - If no code needed, answer directly using the data
    3. For general questions:
       - Answer directly using your knowledge
       - Do NOT mention the DataFrame, CSV file, or data analysis
       - Ignore the uploaded data completely

    User Query: {user_query}
    """
    return model.generate_content(context).text

@cl.on_chat_start
async def start():
    await cl.Message(content="Welcome! Please upload a CSV file.").send()

@cl.on_message
async def main(message: cl.Message):
    global global_df
    
    # Handle file upload
    if message.elements:
        file = message.elements[0]
        
        if not file.name.endswith('.csv'):
            await cl.Message(content="Please upload a CSV file only!").send()
            return
            
        try:
            # Read the CSV file
            df = pd.read_csv(file.path)
            global_df = df
            
            await cl.Message(
                content=f"Upload succeeded! Your CSV file contains {len(df)} rows and {len(df.columns)} columns."
            ).send()
            
            preview = df.head().to_markdown()
            await cl.Message(
                content=f"Here's a preview of your data:\n```\n{preview}\n```\n\nYou can now ask questions about the data!"
            ).send()
            
        except Exception as e:
            await cl.Message(content=f"Error loading the CSV file: {str(e)}").send()
            return
    
    # Handle questions about the data
    else:
        if global_df is None:
            await cl.Message(content="Please upload a CSV file first!").send()
            return
            
        try:
            # Get response from Gemini
            response = handle_query(global_df, message.content)
            await cl.Message(content=response).send()
            
            # If response contains Python code, execute it
            if "```python" in response:
                code = response.split("```python")[1].split("```")[0].strip()
                code = code.replace("df", "global_df")
                
                try:
                    # Execute code and capture output
                    printed_output, result = capture_output(code, global_df)
                    
                    # Display printed output if any
                    if printed_output.strip():
                        await cl.Message(content=f"**Output:**\n```\n{printed_output.strip()}\n```").send()
                    
                    # Display result if any
                    if result is not None:
                        if isinstance(result, pd.DataFrame):
                            output = result.head().to_markdown()
                            await cl.Message(content=f"**Result DataFrame (first 5 rows):**\n```\n{output}\n```").send()
                        elif isinstance(result, pd.Series):
                            output = result.to_markdown()
                            await cl.Message(content=f"**Result Series:**\n```\n{output}\n```").send()
                        else:
                            await cl.Message(content=f"**Result:**\n```\n{str(result)}\n```").send()
                        
                except Exception as e:
                    await cl.Message(content=f"Error executing code: {str(e)}").send()
                    
        except Exception as e:
            await cl.Message(content=f"Error processing query: {str(e)}").send()

if __name__ == "__main__":
    cl.run()