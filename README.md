# azup

Army of robots already here, they are just hiding in datacenters. This is my 
attempt to understand how to manage that army in context of Azure cloud.

I know there are well supported projects that do simular things: 
ARM templates, Terraform and may be more ... and still I want to understand 
cloud from first principles. So here it is. 

I may do simular thing for GCP and AWS later.

## Dev setup

Install all dependencies:
    
    pip install -e .[dev]

Tidy up and run tests:
    
    python setup.py tidy; pytest
    
## Install

Beta:

    pip install -i https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple azup
    
Stable:

    pip install azup
    
## Usage

No much but:

    $ azup
    USAGES:
     azup dump_config <resource_group>
     azup list_images <config_yml>
     azup purge_acr <config_yml>
     azup syncup_apps <config_yml>
    
## YAML config

TODO
 
## 