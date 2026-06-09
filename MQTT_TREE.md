# MQTT Topic Tree

```text
tiot
└── group1
    ├── catalog
    │   ├── devices
    │   │   ├── registration
    │   │   ├── ack
    │   │   │   └── {device_id}
    │   │   └── query
    │   │       ├── {device_id}
    │   │       └── response
    │   │           └── {client_id}
    │   └── services
    │       ├── registration
    │       ├── ack
    │       │   └── {service_id}
    │       └── query
    │           ├── {service_id}
    │           └── response
    │               └── {client_id}
    ├── devices
    │   └── {device_id}
    │       ├── sensors
    │       │   ├── temperature
    │       │   ├── humidity
    │       │   └── motion
    │       └── cmd
    │           ├── thermostat
    │           ├── lights
    │           ├── blinds
    │           └── led
    ├── services
    │   └── {service_id}
    │       ├── register
    │       └── ack
    └── alerts
        └── {device_id}
            ├── temperature
            └── motion

```

## Current implemented flow
- Device registers on `/tiot/group1/catalog/devices/registration`
- Service registers on `/tiot/group1/catalog/services/registration`
- Device asks all devices on `/tiot/group1/catalog/devices/query`
- Device asks one device on `/tiot/group1/catalog/devices/query/{device_id}`
- Bridge replies on `/tiot/group1/catalog/devices/query/response/{client_id}`
- Bridge confirms registration on `/tiot/group1/catalog/devices/ack/{device_id}` or `/tiot/group1/catalog/services/ack/{service_id}`

## Missing topics for full REST coverage
- `/tiot/group1/catalog/services/query`
- `/tiot/group1/catalog/services/query/{service_id}`
- `/tiot/group1/catalog/services/query/response/{client_id}`
- update and delete topic mappings for devices and services
