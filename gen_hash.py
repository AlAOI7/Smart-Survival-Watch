import bcrypt

password = "Admin@123"
hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
print(f"Hash: {hashed}")

# Verify
check = bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
print(f"Verify: {check}")
print(f"\nSQL to run:")
print(f"UPDATE users SET password_hash='{hashed}' WHERE id IN (1,2,3);")
