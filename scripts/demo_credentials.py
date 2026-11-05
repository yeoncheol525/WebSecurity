from lab_support import read_env


if __name__ == "__main__":
    values = read_env()
    for number in (1, 2):
        print(f"user{number}: {values[f'DEMO_USER{number}_PASSWORD']}")
