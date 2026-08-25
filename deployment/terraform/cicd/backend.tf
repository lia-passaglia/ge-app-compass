terraform {
  backend "gcs" {
    bucket = "passaglia-demos-terraform-state"
    prefix = "ge-app-compass/prod"
  }
}
