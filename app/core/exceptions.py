class InvalidStateTransitionError(Exception):
    """Raised when a domain object cannot move to the requested state."""

    def __init__(
        self,
        resource_type: str,
        resource_id: str,
        current_status: str,
        attempted_action: str,
    ):
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.current_status = current_status
        self.attempted_action = attempted_action

        super().__init__(
            f"Cannot perform '{attempted_action}' on {resource_type} "
            f"'{resource_id}' while status is '{current_status}'."
        )