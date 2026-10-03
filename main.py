def main():
    print("Hello from research-agent!")

    while True:
        user_input = input("Query: ")
        if user_input.lower() == "/exit":
            break
        print(f"User input: {user_input}\n >>> Some output")


if __name__ == "__main__":
    main()
