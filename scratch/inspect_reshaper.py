import sys
import arabic_reshaper

sys.stdout.reconfigure(encoding='utf-8')

# Let's inspect arabic_reshaper classes or modules
print(dir(arabic_reshaper))

# Usually, arabic_reshaper has reshaping data. Let's see if we can find it.
# We can look at arabic_reshaper.reshaper.ArabicReshaper
reshaper = arabic_reshaper.ArabicReshaper()
print("Reshaper attributes:", dir(reshaper))

# Let's see if we can find the letters data
# In older/newer versions, it might be in different places.
# Let's write a script to inspect
try:
    import arabic_reshaper.letters as letters
    print("letters attributes:", dir(letters))
except Exception as e:
    print("Failed to import letters:", e)
