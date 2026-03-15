# Example usage in your processing functions:
def process_course_materials(course_code: str):
    """Process all files for a course"""
    file_manager = FileManager()
    files_by_type = file_manager.get_course_files(course_code)
    
    # Process exams for topic frequency
    exam_files = files_by_type.get("exam", [])
    for exam_file in exam_files:
        process_exam(exam_file["file_path"])
    
    # Process assignments for patterns
    assignment_files = files_by_type.get("assignment", [])
    for assignment_file in assignment_files:
        process_assignment(assignment_file["file_path"])
    
    # ... etc.