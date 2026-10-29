# Certificate renewer only; no token creation, revocation, other PKI roles,
# CA changes, venture operations or finance authority.
path "pki-venture/sign/or010-agent"  { capabilities = ["update"] }
path "pki-venture/sign/or010-broker" { capabilities = ["update"] }
path "pki-venture/sign/or010-ceo"    { capabilities = ["update"] }
path "auth/token/renew-self"        { capabilities = ["update"] }
path "auth/token/lookup-self"       { capabilities = ["read"] }
