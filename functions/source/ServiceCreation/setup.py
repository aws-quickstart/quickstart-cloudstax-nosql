import json
import sys
import requests
import time
import socket

import boto3

# example event
# event: {'RequestType': 'Create', 'ServiceToken': 'arn:aws:lambda:us-east-1:497621646529:function:lam-LambdaFunction-1T5JR77VYGBTG', 'ResponseURL': 'https://cloudformation-custom-resource-response-useast1.s3.amazonaws.com/arn%3Aaws%3Acloudformation%3Aus-east-1%3A497621646529%3Astack/lam/98f74630-c1d0-11e7-84b6-50faeaa96461%7CLambdaCustomResource%7C0b637bff-c8f6-4ace-bb6f-1a6e92f29c8a?AWSAccessKeyId=AKIAJNXHFR7P7YGKLDPQ&Expires=1509855955&Signature=fuzleqrW%2BXFf8ncDFJiEhEVn9d4%3D', 'StackId': 'arn:aws:cloudformation:us-east-1:497621646529:stack/lam/98f74630-c1d0-11e7-84b6-50faeaa96461', 'RequestId': '0b637bff-c8f6-4ace-bb6f-1a6e92f29c8a', 'LogicalResourceId': 'LambdaCustomResource', 'ResourceType': 'Custom::CassandraLambdaCustomResource', 'ResourceProperties': {'ServiceToken': 'arn:aws:lambda:us-east-1:497621646529:function:lam-LambdaFunction-1T5JR77VYGBTG', 'Replicas': '3', 'HeapSizeMB': '256', ..., 'JmxRemotePassword'}}

def lambda_handler(event, context):
    reason = 'unknown exception'
    # https://aws.amazon.com/premiumsupport/knowledge-center/best-practices-custom-cf-lambda/
    try:
        print(time.strftime('%Y-%m-%d %H:%M:%S'), event)

        requestType = event['RequestType']
        properties = event['ResourceProperties']

        manageserver='firecamp-manageserver.'+properties['Cluster']+'-firecamp.com'
        # wait till dns is updated for firecamp manageserver
        for i in range(30):
            try:
                print(manageserver, socket.gethostbyname(manageserver))
                break
            except:
                print("lookup manageserver ip error:", sys.exc_info(), manageserver)
                time.sleep(3)

        print(time.strftime('%Y-%m-%d %H:%M:%S'), manageserver, socket.gethostbyname(manageserver))

        if requestType == 'Create':
            encryptVolume = False
            if properties['EncryptVolume'] == "true":
                encryptVolume = True
            encryptJournalVolume = False
            if properties['EncryptJournalVolume'] == "true":
                encryptJournalVolume = True

            data = {
                "Service": {
                    "Region": properties['Region'],
                    "Cluster": properties['Cluster'],
                    "ServiceName": properties['ServiceName']
                },
                "Resource": {
                    "MaxCPUUnits": 0,
                    "ReserveCPUUnits": 256,
                    "MaxMemMB": 0,
                    "ReserveMemMB": int(properties['HeapSizeMB'])
                },
                "Options": {
                    "Replicas": int(properties['Replicas']),
                    "HeapSizeMB": int(properties['HeapSizeMB']),
                    "Volume": {
                        "VolumeType": properties['VolumeType'],
                        "Iops": int(properties['Iops']),
                        "VolumeSizeGB": int(properties['VolumeSizeGB']),
                        "Encrypted": encryptVolume
                    },
                    "JournalVolume": {
                        "VolumeType": properties['JournalVolumeType'],
                        "Iops": int(properties['JournalIops']),
                        "VolumeSizeGB": int(properties['JournalVolumeSizeGB']),
                        "Encrypted": encryptJournalVolume
                    },
                    "JmxRemoteUser": properties['JmxRemoteUser'],
                    "JmxRemotePasswd": properties['JmxRemotePassword']
                }
            }

            print(data)

            url = 'http://' + manageserver + ':27040/?Catalog-Create-Cassandra'
            headers = {'Content-type': 'application/json'}

            # retry 3 times
            reason = 'create service failed'
            succ = False
            for i in range(3):
                try:
                    rsp = requests.put(url, data=json.dumps(data), headers=headers, timeout=60)
                    if rsp.status_code == 200:
                        print(time.strftime('%Y-%m-%d %H:%M:%S'), "service created")
                        succ = True
                        break

                    print(time.strftime('%Y-%m-%d %H:%M:%S'), "create service failed, status_code:", rsp.status_code, "reason:", rsp.reason)
                    reason = rsp.reason
                    time.sleep(5)
                except:
                    print(time.strftime('%Y-%m-%d %H:%M:%S'), "create service error:", sys.exc_info())
                    time.sleep(5)

            if succ != True:
                sendResponse(event, context, 'FAILED', reason, '')
                return

            # wait till service initialized

            url = 'http://' + manageserver + ':27040/?Catalog-Check-Service-Init'
            initdata = {
                "ServiceType": "cassandra",
                "Service": {
                    "Region": properties['Region'],
                    "Cluster": properties['Cluster'],
                    "ServiceName": properties['ServiceName']
                },
            }

            print(time.strftime('%Y-%m-%d %H:%M:%S'), "wait service initialized", initdata)

            reason = 'wait service init timed out'
            for i in range(40):
                try:
                    rsp = requests.get(url, data=json.dumps(initdata), headers=headers, timeout=20)
                    if rsp.status_code == 200:
                        initres = json.loads(rsp.content)
                        print(time.strftime('%Y-%m-%d %H:%M:%S'), "service init status:", initres)
                        if initres["Initialized"]:
                            sendResponse(event, context, 'SUCCESS', '', '')
                            return
                    else:
                        print(time.strftime('%Y-%m-%d %H:%M:%S'), "wait service init failed, status_code:", rsp.status_code, "reason:", rsp.reason)
                        reason = rsp.reason

                    time.sleep(5)
                except:
                    print(time.strftime('%Y-%m-%d %H:%M:%S'), "wait service error:", sys.exc_info())
                    time.sleep(5)

            sendResponse(event, context, 'FAILED', reason, '')
            return

        elif requestType == 'Delete':
            data = {
                "Service": {
                    "Region": properties['Region'],
                    "Cluster": properties['Cluster'],
                    "ServiceName": properties['ServiceName']
                }
            }

            url = 'http://' + manageserver + ':27040/?Delete-Service'
            headers = {'Content-type': 'application/json'}

            # retry 3 times
            reason = 'delete service time out'
            for i in range(3):
                try:
                    rsp = requests.delete(url, data=json.dumps(data), headers=headers, timeout=160)
                    if rsp.status_code == 200:
                        respdata = json.loads(rsp.content)
                        print(time.strftime('%Y-%m-%d %H:%M:%S'), "service deleted, please manually delete the volumes", respdata)

                        if properties['DeleteVolume'] == 'true':
                            print("DeleteVolume is set to true")
                            ec2 = boto3.resource('ec2')
                            for volid in respdata["VolumeIDs"]:
                                volume = ec2.Volume(volid)
                                try:
                                    print(time.strftime('%Y-%m-%d %H:%M:%S'), "volume", volid, "state", volume.state)
                                    for waitVolume in range(5):
                                        if volume.state == "available":
                                            break
                                        else:
                                            time.sleep(5)
                                            volume.load()

                                    volume.delete()
                                    print(time.strftime('%Y-%m-%d %H:%M:%S'), "deleted volume", volid, "state", volume.state)
                                except:
                                    print(time.strftime('%Y-%m-%d %H:%M:%S'), "delete volume", volid, "state", volume.state, "error:", sys.exc_info())

                        sendResponse(event, context, 'SUCCESS', '', respdata)
                        return
                    else:
                        print(time.strftime('%Y-%m-%d %H:%M:%S'), "delete service failed, status_code:", rsp.status_code, "reason:", rsp.reason)
                        reason = rsp.reason
                        time.sleep(5)
                except:
                    print(time.strftime('%Y-%m-%d %H:%M:%S'), "delete service error:", sys.exc_info())
                    time.sleep(5)

            sendResponse(event, context, 'FAILED', reason, '')
            return

        elif requestType == 'Update':
            sendResponse(event, context, 'SUCCESS', '', '')
            return

        else:
            sendResponse(event, context, 'FAILED', reason, '')
            return
    except:
        print(time.strftime('%Y-%m-%d %H:%M:%S'), 'error:', sys.exc_info(), 'event:', event)
        sendResponse(event, context, 'FAILED', reason, '')
        return

# http://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/crpg-ref-responses.html
def sendResponse(event, context, status, reason, responseData):
    try:
        body = {
            'Status': status,
            'Reason': reason,
            'PhysicalResourceId': 'cassandra-' + event['LogicalResourceId'],
            'StackId': event['StackId'],
            'RequestId': event['RequestId'],
            'LogicalResourceId': event['LogicalResourceId']
        }
        if responseData != '':
            body['Data'] = responseData

        print(time.strftime('%Y-%m-%d %H:%M:%S'), 'response body:', body)

        url = event['ResponseURL']
        print(url)

        bodydata = json.dumps(body)
        headers = { 'Content-type': '', 'content-length': str(len(bodydata)) }

        rsp = requests.put(url, data=bodydata, headers=headers)

        print(time.strftime('%Y-%m-%d %H:%M:%S'), 'send response result:', rsp.status_code, 'reason', rsp.reason)
    except:
        print(time.strftime('%Y-%m-%d %H:%M:%S'), 'sendResponse error:', sys.exc_info())

