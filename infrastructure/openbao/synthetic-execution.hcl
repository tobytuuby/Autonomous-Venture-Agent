# Synthetic-only policy. No agent identity is granted this policy or token-create access.
path "auth/token/create" {
  capabilities = ["update"]
}
