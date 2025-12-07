import secrets
import string

class PasswordGenerator:
    """
    Generates password using cryptographically strong randomness.
    """
    def __init__(self, include_upper: bool, include_lower: bool,
        include_digit: bool, include_punct: bool, length: int):

        if not (include_upper or include_lower or include_digit or include_punct):
            raise ValueError("No character types selected as password ingredients.")
        
        if length <= 0:
            raise ValueError("Password length must be at least 1.")

        self.include_upper = include_upper
        self.include_lower = include_lower
        self.include_digit = include_digit
        self.include_punct = include_punct
        self.length = length

    def groups(self) -> list[str]:
        groups = []
        if self.include_lower:
            groups.append(string.ascii_lowercase)
        if self.include_upper:
            groups.append(string.ascii_uppercase)
        if self.include_digit:
            groups.append(string.digits)
        if self.include_punct:
            groups.append(string.punctuation)

        assert len(groups) > 0
        return groups

    def groups_spec(self) -> list[str]:
        groups = []
        if self.include_lower:
            groups.append("a-z")
        if self.include_upper:
            groups.append("A-Z")
        if self.include_digit:
            groups.append("0-9")
        if self.include_punct:
            groups.append("punctuation")

        return groups

    def generate(self) -> str:
        """
        Returns:
            Generated password string
        """
        ingredient_groups = self.groups()
        
        pw = []

        # Stage 1: Generate a random sequence of all password ingredients.
        all_ingredients = "".join(ingredient_groups)
        stage1_length = self.length - len(ingredient_groups)
        for i in range(stage1_length):
            pw.append(secrets.choice(all_ingredients))

        # Stage 2: Add one member of each ingredient group at random insertion points
        # This ensures that at least one member of each ingredient groups
        # will be present in the final password.
        for group_members in ingredient_groups:
            possible_insert_points = range(len(pw)+1)
            insert_point = secrets.choice(possible_insert_points)
            insert_char = secrets.choice(group_members)
            pw.insert(insert_point, insert_char)

        assert len(pw) == self.length

        return "".join(pw)

    def spec(self) -> str:
        ingredients = ", ".join(self.groups_spec())
        return f"{self.length} characters including {ingredients}"

    @classmethod
    def from_template(cls, template: str = "Aaaaaaaaaaaaaa5"):
        """
        Returns PasswordGenerator configured to generate passwords alike the
        specified tempalte string.

        Args:
            template: String like "Aaaaaa!aaaaaaa5" that instructs the function
                which types of characters (lowercase, uppercase, numbers, puncutation)
                should be included in the password and how long the password should
                be. Each type of character found in the template will be included in
                the generated password at least once. If a character type is present
                in template, it does not matter how often it occurs except for the
                total password length.

        Returns:
            PasswordGenerator instance.
        """
        if len(template) == 0:
            raise ValueError("template string must be at least one character long.")

        include_upper = False
        include_lower = False
        include_digit = False
        include_punct = False
        
        for c in template:
            if c.isupper():
                include_upper = True
            elif c.islower():
                include_lower = True
            elif c.isdigit():
                include_digit = True
            elif c in string.punctuation:
                include_punct = True
            else:
                raise ValueError("template string contains unknown characters.")

        return cls(include_upper, include_lower, include_digit, include_punct,
            len(template))
