# Koyeb python sdk

This is the official Python SDK for Koyeb, a platform that allows you to deploy and manage applications and services in the cloud.

# Modules

- `koyeb.api`: Contains the API client and methods to interact with Koyeb's REST API. [Documentation](./docs/api.md)
- `koyeb.sandbox`: Contains the Sandbox module. [Documentation](./docs/sandbox.md)

## Koyeb Sanboxes

A **Kode sandbox** is an isolated, ephemeral environment designed to safely run, test, and experiment with code without affecting other systems or requiring complex setup. It provides developers with a virtualized or containerized execution space where dependencies, environment variables, and runtime contexts can be fully controlled and discarded after use.

You should use a sandbox to:

- Execute untrusted or user-generated code securely
- Prototype applications quickly
- Test APIs or libraries in clean environments
- Demonstrate functionality without configuring local infrastructure

Sandboxes are especially valuable in platforms for AI model evaluation, online coding environments, CI/CD pipelines, and educational tools that require safe, reproducible, and on-demand compute environments.

With **Koyeb Sandboxes**, you can manage fully flexible sandbox environments at scale using the Koyeb Python SDK.

### The Koyeb Sandbox Python module

The Koyeb Sandbox Python module contains functionality to take any actions needed on your sanboxes, including creating and deleting sanboxes, file manipulation, running commands, managing port exposure, and more.

[View the reference for the Sandbox module](./docs/sandbox.md)

[View Sandboxes documentation on the Koyeb website](https://www.koyeb.com/docs/sandboxes)
