(install required packages 'pip install -r requirements.txt')

run:    'python amqpPublisher.py'

options:    
            -m path to message file, default: message.txt  
            -c path to configuration file, default: configuration.txt  
            -t number of messages to send, default: 1  
            -d delay between messages (seconds), default: 1  
