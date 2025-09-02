@Witnessing
Feature: A WebVH controller requests witnessing for log entries and attested resources

    @Witnessing-001
    Scenario: Author connects to witness service
        Given there is a new author agent "bob"
        And the endorser service is running
        And the witness plugin is configured
        And the witness has an open invitation
        When "bob" receives the invitation
        Then "bob" has an active witness connection

    @Witnessing-002
    Scenario: Author publishes an initial did log entry
        Given there is a new author agent "bob"
        And the endorser service is running
        And the witness plugin is configured
        And the witness has an open invitation
        When "bob" receives the invitation
        Then "bob" has an active witness connection
        Then "bob" creates an initial log entry
        And the witness approved the log entry
        Then "bob" has a published did
