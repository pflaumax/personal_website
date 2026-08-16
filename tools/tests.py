from django.test import TestCase
from django.urls import reverse


class ToolsPageSmokeTests(TestCase):
    def test_tools_page_renders(self):
        response = self.client.get(reverse("tools:tools"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Todo List")
        self.assertContains(response, "Pomodoro Timer")
