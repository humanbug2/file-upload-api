import json
import os
import psycopg2
import urllib.request
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin

app = Flask(__name__)
CORS(app, support_credentials=True)
@app.route("/", methods = ['GET', 'POST'])
@cross_origin(supports_credentials=True)

def lambda_handler():
    if request.method=='POST':
        
        request_data = request.get_json()
        username = request_data.get('name')
        useremail = request_data.get('email')
        emailSubject = request_data.get('subject')
        emailMessage = request_data.get('message')
        emailAttachments = request_data.get('fileLocations')
        # username = 'Manroop'
        # useremail = 'manroop.singh@procdna.com'
        # emailSubject = 'Testing out email'
        # emailMessage = 'message of email'
        # emailAttachments = ['https://auxo-form-responses.s3.amazonaws.com/General+Media+screen.png','https://auxo-form-responses.s3.amazonaws.com/Payments.png']


        # Configure SMTP
        smtp_server = 'smtp.gmail.com'
        smtp_port = 587
        smtp_username = 'manroopparmar120@gmail.com'
        smtp_password = 'hzlrevhesnzatlju'
        
        try:
            conn = psycopg2.connect(
                host="auxo-staging-migrated.cm6vbnnsye5g.us-east-1.rds.amazonaws.com",
                port=5432,
                database="Auxo-Database",
                user="auxoAdmin",
                password="Password123"
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
            for url in emailAttachments:
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
                    sql = f"INSERT INTO help_section_contact_forms (name, email, subject, message, attachments) VALUES('{username}', '{useremail}', '{emailSubject}', '{emailMessage}', '{','.join(emailAttachments)}')"
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
    else: 
        return jsonify({'message': 'hello world'})

if __name__ == '__main__':
    app.run(host='0.0.0.0')