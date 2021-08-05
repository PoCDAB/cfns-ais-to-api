from pyais import decode_msg

file = open('ais.txt', 'r')
for line in file.readlines():
    try:
        decoded = decode_msg(line)
        print(decoded)
    except:
        continue