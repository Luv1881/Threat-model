bash setup.sh

## IriusRisk StartLeft — generate OTM from Terraform

```bash
DEFAULT_MAPPING="venv/lib/python3.12/site-packages/tests/resources/terraform/iriusrisk-tf-aws-mapping.yaml"

venv/bin/startleft parse \
  --iac-type TERRAFORM \
  --default-mapping-file "$DEFAULT_MAPPING" \
  --custom-mapping-file terraform/startleft-mapping.yaml \
  --project-name "VaultNote" \
  --project-id "vaultnote" \
  --output-file vaultnote-iriusrisk.otm \
  terraform/variables.tf \
  terraform/main.tf \
  terraform/vpc.tf \
  terraform/alb.tf \
  terraform/ecs.tf \
  terraform/rds.tf \
  terraform/elasticache.tf \
  terraform/s3.tf \
  terraform/secrets.tf
```

Output: `vaultnote-iriusrisk.otm` — import into IriusRisk via **File → Import OTM**.