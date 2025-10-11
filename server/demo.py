
def testNone():
    return None

def main():
    str_list = "aaa:bbb:ccc".split(':')
    print("========")
    for word in str_list:
        print(f"word:{word}")
    print("========")

if __name__ == '__main__':
    main()