import json, os, psycopg2, urllib.request, smtplib, boto3, ast, concurrent.futures
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from fastapi import FastAPI,Request
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables from .env file
load_dotenv()
origins = [
    "https://auxo-frontend.vercel.app",    # staging frontend
    "https://app.auxo.tech",               # production frontend
    "http://localhost:8000",
    "http://localhost:3000",
]
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Access environment variables
s3_bucket_name = os.getenv("S3_BUCKET_NAME")
aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
aws_region = os.getenv("AWS_REGION")
auxo_staging_host = os.getenv("AUXO_STAGING_HOST")
auxo_staging_port = os.getenv("AUXO_STAGING_PORT")
auxo_staging_database = os.getenv("AUXO_STAGING_DATABASE")
auxo_staging_user = os.getenv("AUXO_STAGING_USER")
auxo_staging_password = os.getenv("AUXO_STAGING_PASSWORD")
api_default_endpoint = os.getenv("API_DEFAULT_ENDPOINT")

s3 = boto3.client('s3', aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key, region_name=aws_region)

@app.get(api_default_endpoint + "/")
def read_root():
    return "Hello World !!!"

@app.post(api_default_endpoint + "/upload")
def upload_files(raw_files):
    try:    
        files = json.loads(raw_files.replace("'", '"'))

        # Handle each file in parallel using ThreadPoolExecutor
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(upload_file_to_s3,file) for file in files]
            concurrent.futures.wait(futures)

        # Get the results from the futures
        upload_results = [future.result() for future in futures]

        response = {
            'statusCode': 200,
            'headers': {            
                'Access-Control-Allow-Headers': 'Content-Type',             
                'Access-Control-Allow-Origin': ['*'],             
                'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'        
            },
            'body': upload_results,
            }
        return response
    except Exception as err:
        print("Error: {}".format(err))
        response = {
            'statusCode': 500,
            'body': json.dumps({'message': "Error"}),
        }
        return response
    
def upload_file_to_s3(file):
    file_val = file.get('name')
    file_name = secure_filename(file_val)
    try:
        # Upload the file to S3
        s3.put_object(Bucket=s3_bucket_name, Key=file_name)
        # Provide the S3 URL to the uploaded file
        file_url = f'https://{s3_bucket_name}.s3.{aws_region}.amazonaws.com/{file_name}'
        return {'file_name': file_name, 's3_location': file_url}
    except Exception as e:
        return {'file_name': file_name, 'error': str(e)}
    

@app.post(api_default_endpoint + "/submit")
def send_email(request: Request):
    try:
        username = request.query_params.get("name")
        useremail = request.query_params.get("email")
        emailSubject = request.query_params.get("subject")
        emailMessage = request.query_params.get("message")
        emailAttachments = request.query_params.get("fileLocations")
        emailAttachmentsList = ast.literal_eval(emailAttachments)

        # Configure SMTP
        smtp_server = 'smtp.gmail.com'
        smtp_port = 587
        smtp_username = 'manroopparmar120@gmail.com'
        smtp_password = 'hzlrevhesnzatlju'
        
        try:
            conn = psycopg2.connect(
                host=auxo_staging_host,
                port=auxo_staging_port,
                database=auxo_staging_database,
                user=auxo_staging_user,
                password=auxo_staging_password
            )
            cursor = conn.cursor()

            # Verify SMTP connection
            try:
                server = smtplib.SMTP(smtp_server, smtp_port)
                server.starttls()
                server.login(smtp_username, smtp_password)
            except Exception as e:
                return {
                    'statusCode': 500,
                    'body': json.dumps({'SMTP configuration error': str(e)})
                }

            # Email configuration
            msg = MIMEMultipart()
            msg['From'] = 'ProcdnaBot <manroopparmar120@gmail.com>'
            msg['To'] = 'roop4905@gmail.com'
            msg['Subject'] = emailSubject

            # Email body
            body_text = f"""
            Sent from: {useremail}
            Name: {username}
            {emailMessage}
            """
            msg.attach(MIMEText(body_text, 'html'))
            # Attach images
            for url in emailAttachmentsList:
                response = urllib.request.urlopen(url)
                img_data = response.read()
                image = MIMEImage(img_data, name=os.path.basename(url))
                msg.attach(image)
               
            # Send email
            try:
                server.sendmail(smtp_username, 'roop4905@gmail.com', msg.as_string())
            except Exception as e:
                return {
                    'statusCode': 500,
                    'body': json.dumps({'error': str(e)})
                }
            finally:
                server.quit()

            # Insert data into MySQL
            try:
                with conn.cursor() as cursor:
                    sql = f"INSERT INTO help_section_contact_forms (name, email, subject, message, attachments) VALUES('{username}', '{useremail}', '{emailSubject}', '{emailMessage}', '{emailAttachments}')"
                    cursor.execute(sql)
                    conn.commit()
            except Exception as e:
                return {
                    'statusCode': 500,
                    'body': json.dumps({'error': str(e)})
                }
            finally:
                conn.close()

            response = {
                        'statusCode': 200,
                        'headers': {            
                            'Access-Control-Allow-Headers': 'Content-Type',             
                            'Access-Control-Allow-Origin': ['*', 'http://localhost:3000'],             
                            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'        
                        },
                        'body': json.dumps({'message': "Success"}),
                    }
            return response
        except Exception as err:
            print("Error: {}".format(err))
            response = {
                'statusCode': 500,
                'body': json.dumps({'message': "Error"}),
            }
            return response
    except Exception as e: 
        return {'error': e}

# files = [
        #     {
        #         path: "error.png",
        #         preview: "blob:http://localhost:3000/ad879eb3-5e8a-4ec1-bbea-556675baef14",
        #         lastModified: 1699514748122,
        #         name: "error.png",
        #         size: 78938,
        #         type: "image/png"
        #     },
        #     {
        #         path: "Physician universe (selected hcp).png",
        #         preview: "blob:http://localhost:3000/474c935e-7e1b-47de-a427-4b2c8428e9d2",
        #         lastModified: 1698672559633,
        #         name: "Physician universe (selected hcp).png",
        #         size: 1541501,
        #         type: "image/png"
        #     }
        # ]
        # files = [{'filename': 'error.png'}, {'filename': 'Physician universe (selected hcp).png'}]