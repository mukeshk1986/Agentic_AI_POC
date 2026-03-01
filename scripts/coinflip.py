import random
print("I will flip a coin 1000 times. Guess how many times it will land on heads. (Press enter to begin)")
input()
flips = 0
heads = 0
while flips < 1000:
    if random.randint(0, 1) == 0:
        heads = heads + 1
    flips = flips + 1

    if flips == 900:
        print("900 flips and there have been " + str(heads) + " heads.")
    if flips ==100:
        print("At 100 tosses, heads has come up " + str(heads) + " times so far")
    if flips ==500:
        print("Halfway done, heads has come up " + str(heads) + " times")

print()
print("Out of 1000 flips, heads came up " + str(heads) + " times.")
print("Were you close?")