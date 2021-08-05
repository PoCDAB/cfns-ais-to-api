import sys
import socket
import serial
from http.client import HTTPConnection
from base64 import b64encode
from requests import get
from pyais import decode_msg
from datetime import datetime
from pytz import timezone

# Get the serial USB port for AIS
ser = serial.Serial(
    port="/dev/ttyUSB0", baudrate=38400, bytesize=8, stopbits=serial.STOPBITS_ONE
)
ser.flushInput()

# This sets up the https connection
baseurl = 'driel.rh.nl'
port = 65533
conn = HTTPConnection(baseurl, port, timeout=10)
username = 'daniel'
password = 'geerts'
# Encode AUTH as Base64 and then decode it to ascii as python stores it as a byte string
print("Please enter webapp API username:")
username = input()
print("Please enter webapp API password:")
password = input()
encodedUserAndPass = "{}:{}".format(username, password).encode("ascii")
userAndPass = b64encode(encodedUserAndPass).decode("ascii")
headers = {'Authorization':'Basic '+ userAndPass, 'Content-type':'application/json', 'Accept':'application/json' }
print()

# Get name and public API of this device
pc_name = socket.gethostname()
public_ip = get('https://api.ipify.org').text

def is_API_reachable():
    connection = HTTPConnection(baseurl, port)
    connection.request("GET", "/api/V1/", headers=headers)
    r = connection.getresponse()
    print("API reachable: ", r.status, r.reason)
    connection.close()
    return r.status is 200

def send_to_API(ser_bytes):
    amsterdam = timezone('Europe/Amsterdam')
    currentTimeAmsterdam = amsterdam.localize(datetime.now())
    json_data = '{"received_from": "' + pc_name + public_ip + '", "received_at": "' + str(currentTimeAmsterdam) + '", "message": "' + ser_bytes + '" }'
    print(json_data)
    
    # Then connect
    conn.request('POST', '/api/V1/ais/', json_data, headers=headers)

    #Get response back
    res = conn.getresponse()
    data = res.read()
    print("Status: ", res.status, res.reason)

def decode_AIS(ser_bytes):
    try:
        msg = decode_msg(ser_bytes)
        return msg
    except:
        print("Unexpected error while decoding AIS:", sys.exc_info())

def decode_binary_string(s, bit=6):
    text = ''
    for i in range(0, len(s), bit):
        bit_char = s[i: int(i+bit)]
        if (bit==6):
            bit_char = '01' + bit_char
        text += ''.join([chr(int(bit_char, 2))])
    return text

def print_ais_message_data(decoded_msg, keys):
    if decoded_msg:
        print("----------")
        for i in decoded_msg:
            for key in keys:
                if str(i) is key:
                    print (i, decoded_msg[i])
                    if 'data' is key:
                        stripped = decoded_msg[i]
                        otherres = decode_binary_string(stripped, 6)
                        print('6bit:', otherres)
                        otherres = decode_binary_string(stripped, 8)
                        print('8bit:', otherres)
        print("----------")


keep_running = True
test = False

# While always: Get all AIS messages from AIS
while keep_running:
    if test: # Only decoded test AIS strings. Does NOT send to API.
        test_ais = ['!AIVDM,1,1,,B,83`I7@h0BTUlp522Dp2Dp0H4PDl0QDTVH51Dl@0,2*50',
                    '!AIVDM,1,1,,A,83`I7@hP8453Bk`n=ji=DILr<@,4*2E',
                    '!AIVDM,1,1,,B,>>M4fWA<59B1@E=@,0*17',
                    '!AIVDM,1,1,1,B,8>h8nkP0Glr=<hFI0D6??wvlFR06EuOwgwl?wnSwe7wvlOw?sAwwnSGmwvh0,0*17',
                    '!AIVDM,1,1,,A,83`l7@hP8453Bk`n=ji=DlLr<@,4*2E',
                    '!AIVDM,1,1,,A,83`l7@hP8453Bk`n=ji=DlLr=2iBDm=9>S8h;5=>DS`e<@,4*05']
        for test in test_ais:
            decoded_msg = decode_AIS(test)
            print_ais_message_data(decoded_msg, ['type', 'fid', 'data'])

            print('================================================')

        # End the test run.
        keep_running = False

    else: # the real deal !! Sends serial AIS to webapp API
        ser_bytes = ser.readline().decode("UTF-8").replace('\r\n', '')
        print(ser_bytes)
        decoded_msg = decode_AIS(ser_bytes)
        print_ais_message_data(decoded_msg, ['type', 'fid', 'data'])
        
        if is_API_reachable():
            send_to_API(ser_bytes)
        else:
            print("API offline or login is false")
            keep_running = False

        print('================================================')

conn.close()