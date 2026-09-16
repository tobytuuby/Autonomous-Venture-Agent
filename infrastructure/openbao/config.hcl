ui = false
disable_mlock = true
api_addr = "http://127.0.0.1:8200"
cluster_addr = "http://127.0.0.1:8201"

listener "tcp" {
  address     = "127.0.0.1:8200"
  tls_disable = true
}

storage "file" {
  path = "/var/lib/openbao/data"
}

audit "file" "security" {
  description = "P0 security audit log"
  options {
    file_path = "/var/log/openbao/audit.log"
    mode      = "0600"
  }
}
