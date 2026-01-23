# CHANGELOG

<!-- version list -->

## v1.3.0 (2026-01-23)

### Bug Fixes

- User serializer details fix
  ([`20d5906`](https://github.com/Antoney20/RACI-Project-Management-System/commit/20d5906f1a453ec209b82018bee603e065cf268d))

- **core**: Update PostgreSQL settings, reset migrations, and fix project logic
  ([`a4ad61b`](https://github.com/Antoney20/RACI-Project-Management-System/commit/a4ad61beb4ec0a8c53eeef4e194a8dee06504e3e))

### Features

- Add Scientific Coordinator PDF and update serializers and views for project management
  ([`d2db429`](https://github.com/Antoney20/RACI-Project-Management-System/commit/d2db42981fa3a88e92f66d3974dee50ddc94a1b1))

- Align the leave request to the org needs
  ([`cc1d60f`](https://github.com/Antoney20/RACI-Project-Management-System/commit/cc1d60f393c23d0f2dec22f28540b84c0cd6ceb6))

- Deployment to live server
  ([`afc511f`](https://github.com/Antoney20/RACI-Project-Management-System/commit/afc511f4ff9591a10e2ddb90c5ba92264fe520c9))

- Enhance project management with RACI assignments, milestone tracking, and document handling
  ([`2077536`](https://github.com/Antoney20/RACI-Project-Management-System/commit/20775360bc176ae518607967fdf72c54e37a0d30))

- Implement chat group, conversation, and message models with serializers and views
  ([`0cdf69e`](https://github.com/Antoney20/RACI-Project-Management-System/commit/0cdf69ef0d6831c82743db8af822bc535415ed1b))

- Implement project management features
  ([`4e6e818`](https://github.com/Antoney20/RACI-Project-Management-System/commit/4e6e8182f25d4419094176ec48169200f702ab81))

- Implement user invitation system with invite management and acceptance flow
  ([`8c1b917`](https://github.com/Antoney20/RACI-Project-Management-System/commit/8c1b9176cea335a07e3d016d26c8365eb0a97719))

- Initialize chat app with models, views, admin, and migrations
  ([`8e7481a`](https://github.com/Antoney20/RACI-Project-Management-System/commit/8e7481a75c8f1d8e71ebcb7ced34cb632b00069e))

- Initialize project structure with models, views, and admin setup
  ([`59fa467`](https://github.com/Antoney20/RACI-Project-Management-System/commit/59fa467e1ceeb0d2d313d60e80be90bf5264f970))

- Manage users
  ([`e8af452`](https://github.com/Antoney20/RACI-Project-Management-System/commit/e8af45269d761e127daaab336de9f1ff54343c53))

- Manage users well
  ([`55d83d0`](https://github.com/Antoney20/RACI-Project-Management-System/commit/55d83d0a1ad5fad4439c36c4efe08770880278da))

- Update leave allocation model and serializers to enhance leave management functionality
  ([`e409fbc`](https://github.com/Antoney20/RACI-Project-Management-System/commit/e409fbcd85535897368f0592778e821c86c59c81))

- Update project model and serializers for improved project management functionality
  ([`4c73f3d`](https://github.com/Antoney20/RACI-Project-Management-System/commit/4c73f3dd90dd1ba3a6b5cb932c924cdfe5d4e8ed))

- **accounts**: Extend account serializer and views
  ([`a054e22`](https://github.com/Antoney20/RACI-Project-Management-System/commit/a054e221928231b8423f97104314ee314b811858))

- **accounts,mint**: Update views, serializers, and routing
  ([`417f13d`](https://github.com/Antoney20/RACI-Project-Management-System/commit/417f13d1316945996528bf2566e747b486ea5c0c))

- **calendar**: Implement calendar event synchronization for leave requests, project deadlines, and
  milestones; add public holiday model and serializer
  ([`a5c38fb`](https://github.com/Antoney20/RACI-Project-Management-System/commit/a5c38fbaf93d4f71db12a4ab9a17f2c18e1afe5c))

- **employee**: Initialize employee app with models, views, and admin registration
  ([`8fdfde5`](https://github.com/Antoney20/RACI-Project-Management-System/commit/8fdfde5c14c8ef3a5134948c04676d4ceed08a96))

- **hr**: Extend employee models, contracts, and leave logic
  ([`2f541f3`](https://github.com/Antoney20/RACI-Project-Management-System/commit/2f541f3948cf8e26a32f79c206e9d150f24b26ec))

- **mint**: Add project and milestone comments and notes functionality, manage commands for leave
  ([`918ad23`](https://github.com/Antoney20/RACI-Project-Management-System/commit/918ad239870ce20af8b981f2ed42b4b4d75021c2))

- **project**: Enhance supervisor notification functionality and improve project model serializers
  ([`430cc14`](https://github.com/Antoney20/RACI-Project-Management-System/commit/430cc14db69db69a1603c4420d8c734e0bcf67e7))

- **review**: Add project review and comment models, serializers, and cron job for moving completed
  projects to review
  ([`b026f10`](https://github.com/Antoney20/RACI-Project-Management-System/commit/b026f10f0e1daf1e96a19364294a94be761b8e9b))

- **review**: Implement project review and comment functionality, including models, serializers, and
  viewsets
  ([`03bf5e4`](https://github.com/Antoney20/RACI-Project-Management-System/commit/03bf5e4f2171c1794ef2b5bd21b6697e0a9936b3))

- **review**: Implement project review creation logic and integrate with project completion
  workflow.. added a review seervice to backup the cronjob
  ([`d1ccb7b`](https://github.com/Antoney20/RACI-Project-Management-System/commit/d1ccb7b620abf31a2b30c3387098d6dd28570448))


## v1.2.0 (2025-12-03)

### Features

- Add Mint app for project and task management
  ([`e0ef638`](https://github.com/Antoney20/RACI-Project-Management-System/commit/e0ef63865f8e29cfd358601cd0273f5eef0e118b))

- Enhance user role definitions and implement email verification process
  ([`4c36bed`](https://github.com/Antoney20/RACI-Project-Management-System/commit/4c36bed8e783afe52f2641c7cb96d2c79ef2b697))

- Implement leave allocation management with CRUD operations and carryover functionality
  ([`58866af`](https://github.com/Antoney20/RACI-Project-Management-System/commit/58866af1c00446a5b2e079015fb3e3da5d4e2cc7))

- Refactor email services and add password reset email templates
  ([`d3d9dfa`](https://github.com/Antoney20/RACI-Project-Management-System/commit/d3d9dfa8992ff318d543e5dfa83d1989ed116e11))

- Rest framework settings
  ([`b65aa7f`](https://github.com/Antoney20/RACI-Project-Management-System/commit/b65aa7f6aabc83988f12531e0d7ba98ea35cc223))

- Update user model to use BigAutoField and enhance leave management features
  ([`cea3a47`](https://github.com/Antoney20/RACI-Project-Management-System/commit/cea3a47938c7dcce594537f400a5716cdda1e091))


## v1.1.0 (2025-12-02)

### Features

- Implement initial migration for CustomUser and TokenBlacklist models
  ([`a8ca0a1`](https://github.com/Antoney20/RACI-Project-Management-System/commit/a8ca0a1cdffc9f85388071b30116eab3a32902f8))

- Initial Accounts setup, has auth logic for multiple users
  ([`3cb92ae`](https://github.com/Antoney20/RACI-Project-Management-System/commit/3cb92ae1271ab4494d62630f7c5b14096b829a1d))


## v1.0.0 (2025-12-02)

- Initial Release
