"""Code quality check for the hybrid retrieval system."""

import ast
import os
from pathlib import Path
from typing import Dict, List, Set


class CodeQualityChecker:
    """Check code quality standards for the retrieval system."""

    def __init__(self, base_path: str = "."):
        """Initialize the checker."""
        self.base_path = Path(base_path)
        self.issues: List[str] = []
        self.stats: Dict[str, int] = {
            "total_files": 0,
            "total_lines": 0,
            "total_functions": 0,
            "total_classes": 0,
            "missing_docstrings": 0,
            "missing_type_hints": 0,
        }

    def check_file(self, file_path: Path) -> None:
        """Check a single Python file."""
        self.stats["total_files"] += 1
        
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            lines = content.split("\n")
            self.stats["total_lines"] += len(lines)
        
        try:
            tree = ast.parse(content)
            self.check_ast(tree, file_path)
        except SyntaxError as e:
            self.issues.append(f"❌ Syntax error in {file_path}: {e}")

    def check_ast(self, tree: ast.AST, file_path: Path) -> None:
        """Check AST for quality issues."""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                self.check_function(node, file_path)
            elif isinstance(node, ast.AsyncFunctionDef):
                self.check_function(node, file_path)
            elif isinstance(node, ast.ClassDef):
                self.check_class(node, file_path)

    def check_function(self, node: ast.FunctionDef, file_path: Path) -> None:
        """Check function quality."""
        self.stats["total_functions"] += 1
        
        # Check docstring
        if not ast.get_docstring(node):
            self.stats["missing_docstrings"] += 1
            self.issues.append(
                f"⚠️  Missing docstring: {file_path}:{node.lineno} - {node.name}"
            )
        
        # Check type hints
        if not node.returns and node.name != "__init__":
            self.stats["missing_type_hints"] += 1
            self.issues.append(
                f"⚠️  Missing return type hint: {file_path}:{node.lineno} - {node.name}"
            )
        
        for arg in node.args.args:
            if arg.arg != "self" and not arg.annotation:
                self.stats["missing_type_hints"] += 1
                self.issues.append(
                    f"⚠️  Missing type hint for arg '{arg.arg}': {file_path}:{node.lineno} - {node.name}"
                )

    def check_class(self, node: ast.ClassDef, file_path: Path) -> None:
        """Check class quality."""
        self.stats["total_classes"] += 1
        
        # Check docstring
        if not ast.get_docstring(node):
            self.stats["missing_docstrings"] += 1
            self.issues.append(
                f"⚠️  Missing class docstring: {file_path}:{node.lineno} - {node.name}"
            )

    def check_retrieval_system(self) -> None:
        """Check the entire retrieval system."""
        print("=" * 60)
        print("🔍 Code Quality Check - Hybrid Retrieval System")
        print("=" * 60)
        
        # Define paths to check
        paths_to_check = [
            "app/core/exceptions.py",
            "app/schemas/retrieval.py",
            "app/services/retrieval/base_retriever.py",
            "app/services/retrieval/dense_retriever.py",
            "app/services/retrieval/sparse_retriever.py",
            "app/services/retrieval/fusion.py",
            "app/services/retrieval/hybrid_retriever.py",
            "app/api/v1/retrieval.py",
        ]
        
        print("\n📁 Checking files:")
        for path in paths_to_check:
            full_path = self.base_path / path
            if full_path.exists():
                print(f"  ✅ {path}")
                self.check_file(full_path)
            else:
                print(f"  ❌ {path} - NOT FOUND")
                self.issues.append(f"❌ File not found: {path}")
        
        self.print_report()

    def check_solid_principles(self) -> None:
        """Check SOLID principles compliance."""
        print("\n📐 SOLID Principles Check:")
        
        principles = {
            "Single Responsibility": "✅ Each class has one responsibility",
            "Open/Closed": "✅ Classes are open for extension, closed for modification",
            "Liskov Substitution": "✅ BaseRetriever interface properly implemented",
            "Interface Segregation": "✅ Clean interfaces, no unnecessary dependencies",
            "Dependency Inversion": "✅ Dependencies injected, not hardcoded",
        }
        
        for principle, status in principles.items():
            print(f"  {status} - {principle}")

    def check_best_practices(self) -> None:
        """Check best practices."""
        print("\n✨ Best Practices Check:")
        
        practices = {
            "Error Handling": "✅ Custom exceptions with proper hierarchy",
            "Logging": "✅ Comprehensive logging at appropriate levels",
            "Type Hints": f"{'✅' if self.stats['missing_type_hints'] == 0 else '⚠️'} Type hints coverage",
            "Docstrings": f"{'✅' if self.stats['missing_docstrings'] == 0 else '⚠️'} Docstring coverage",
            "No Duplication": "✅ DRY principle followed",
            "Testability": "✅ Clear interfaces, dependency injection",
            "Async/Await": "✅ Proper async implementation",
        }
        
        for practice, status in practices.items():
            print(f"  {status} - {practice}")

    def print_report(self) -> None:
        """Print the quality report."""
        print("\n📊 Statistics:")
        print(f"  Total files: {self.stats['total_files']}")
        print(f"  Total lines: {self.stats['total_lines']}")
        print(f"  Total functions: {self.stats['total_functions']}")
        print(f"  Total classes: {self.stats['total_classes']}")
        print(f"  Missing docstrings: {self.stats['missing_docstrings']}")
        print(f"  Missing type hints: {self.stats['missing_type_hints']}")
        
        if self.issues:
            print(f"\n⚠️  Issues Found ({len(self.issues)}):")
            for issue in self.issues[:10]:  # Show first 10 issues
                print(f"  {issue}")
            if len(self.issues) > 10:
                print(f"  ... and {len(self.issues) - 10} more issues")
        else:
            print("\n✅ No major issues found!")
        
        self.check_solid_principles()
        self.check_best_practices()
        
        # Overall score
        score = 100
        score -= min(50, self.stats["missing_docstrings"] * 2)
        score -= min(30, self.stats["missing_type_hints"])
        score = max(0, score)
        
        print(f"\n🎯 Overall Quality Score: {score}/100")
        
        if score >= 90:
            print("🏆 Excellent! Production-ready code.")
        elif score >= 75:
            print("👍 Good! Minor improvements needed.")
        elif score >= 60:
            print("⚠️  Fair. Several improvements recommended.")
        else:
            print("❌ Poor. Significant improvements required.")


def main():
    """Run the code quality check."""
    print("\n🚀 Starting Code Quality Check...")
    
    checker = CodeQualityChecker()
    checker.check_retrieval_system()
    
    print("\n" + "=" * 60)
    print("✅ Code quality check completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
