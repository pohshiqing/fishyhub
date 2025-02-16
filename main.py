import os
import psycopg2
import requests
from PIL import Image
from io import BytesIO
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

# Assuming the environment variable for Google API key is set up
os.environ["GOOGLE_API_KEY"] = "AIzaSyBye8655_9fWe0xnHz7fYoo9AIPka1ZvdE"

# Set up the Gemini API with LangChain
chat_model = ChatGoogleGenerativeAI(model="gemini-pro")

def generate_product_description(image_url, product_name):
    try:
        # Download the image from the URL
        response = requests.get(image_url)
        if response.status_code != 200:
            return f"Error downloading image: {response.status_code}"
    
        # Prepare the image data
        img_data = BytesIO(response.content)
    
        # Construct the system and user prompts
        system_prompt = (
            "You are a product operations specialist of Fishyhub, an online aquarium fish marketplace that sells many live fishes to customers on our website. "
            "Your job is to generate a professional, engaging, respectful, and SEO-friendly product description that does not include any promotions and discounts."
        )
    
        user_prompt = (
            f"In the first paragraph, generate a short, engaging product description for the following product: '{product_name}' "
            "and based on the image provided. Keep the description concise (around 2-3 sentences) and ensure it resonates with both novice and experienced aquarium enthusiasts. "
            "In a second section, using only the product name, write a detailed description in bullet points, covering water conditions, tank mates, feeding habit, and care."
            "Please do not add any section titles (Product Description, **Product Description:** etc.), just show the content."
        )
    
        # Prepare the request payload
        payload = {
            'product_name': product_name,
            'system_prompt': system_prompt,
            'user_prompt': user_prompt,
        }
    
        # Make the request to the Gemini model API
        response = chat_model.invoke([HumanMessage(content=user_prompt, additional_kwargs={"image": img_data})])
        return response.content if response else "No description generated."
    except Exception as e:
        return f"Error generating description: {str(e)}"


def clean_text_for_sql(text):
    # Replace common problematic characters with safer alternatives
    replacements = {
        '°': ' degrees',        # Replace degree symbol with "degrees"
        '–': '-',               # Replace en dash with hyphen
        '‘': "'",              # Replace left single quote with apostrophe
        '’': "'",              # Replace right single quote with apostrophe
        '“': '"',              # Replace left double quote with quotation mark
        '”': '"',              # Replace right double quote with quotation mark
        '—': '-',              # Replace em dash with hyphen
        '©': '(c)',            # Replace copyright symbol with "(c)"
    }
    
    # Iterate through replacements and apply them
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    # Encode to UTF-8 and return
    try:
        # Attempt to encode the text to UTF-8 and decode back to string
        return text.encode('utf-8', 'replace').decode('utf-8')
    except UnicodeEncodeError:
        return text


def update_ai_product_descriptions():
    DB_NAME = "production"
    DB_USER = "shiqing_read_n_view"
    DB_PASSWORD = "sQ5789@a$29!"
    DB_HOST = os.getenv("DB_HOST", "remote")
    DB_PORT = "5432"

    # Initialize a Python array to store the descriptions
    product_descriptions = []

    try:
        with psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        ) as conn:
            with conn.cursor() as cursor:
                # Step 1: Fetch product details
                cursor.execute(
                    "SELECT id, product_name, product_image FROM product WHERE category_id = 1 "
                    "AND status = 'active' AND qty > 0 AND (length(more_description) < 10 OR lower(more_description) LIKE '%whatsapp%' OR lower(more_description) LIKE '%telegram%') "
                    "ORDER BY id DESC LIMIT 100;"  # Modify the LIMIT as needed
                )
                rows = cursor.fetchall()
                
                # Step 2: Generate descriptions and store them in the Python array
                for row in rows:
                    product_id, product_name, product_image = row
                    print(f"Product ID: {product_id}")
                    print(f"Product Name: {product_name}")
                    print(f"Product Image URL: {product_image}")

                    # Generate AI description based on image and product name
                    description = generate_product_description(product_image, product_name)
                    description = clean_text_for_sql(description)  # Clean the description text

                    print("Generated Product Description:")
                    print(description)

                    # Add description and product_id to the list (array)
                    product_descriptions.append({
                        "product_id": product_id,
                        "ai_description": description
                    })
                
                # Step 3: Create the view based on the array of product descriptions
                # Safely escape the values and prepare them for the SQL query
                descriptions_values = ", ".join([f"({item['product_id']}, '{item['ai_description'].replace("'", "''")}')" for item in product_descriptions])
                
                # Create the view directly with the array of descriptions
                cursor.execute(f"""
                    CREATE OR REPLACE VIEW ai_product_descriptions AS
                    SELECT product_id, ai_description
                    FROM (VALUES {descriptions_values}) AS temp_product_descriptions(product_id, ai_description);
                """)

                # Commit the changes
                conn.commit()

    except Exception as e:
        print("Error:", e)

    # For testing: Print the generated descriptions stored in the array
    print("\nGenerated Descriptions Array:")
    print(product_descriptions)


if __name__ == "__main__":
    update_ai_product_descriptions()
