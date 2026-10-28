# OR-0.10 restricted certificate issuer policy.
# The broker and agents NEVER receive this token.
path "pki-venture/issue/or010-broker" {
  capabilities = ["update"]
}
path "pki-venture/issue/or010-agent" {
  capabilities = ["update"]
}
path "pki-venture/cert/ca" {
  capabilities = ["read"]
}
path "pki-venture/ca/pem" {
  capabilities = ["read"]
}
