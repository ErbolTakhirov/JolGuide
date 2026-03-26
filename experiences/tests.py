from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils.timezone import now
from datetime import timedelta

from accounts.models import GuideProfile
from .models import Experience, ExperienceBooking, ExperienceReview

User = get_user_model()


class ExperienceModelTests(TestCase):
    def setUp(self):
        self.guide_user = User.objects.create_user(
            email='guide@test.com', username='guide', password='test1234', role='guide',
        )
        self.guide = GuideProfile.objects.create(
            user=self.guide_user, name='Test Guide', city='Бишкек',
            languages='ru', bio='Bio', is_verified=True,
        )
        self.tourist = User.objects.create_user(
            email='tourist@test.com', username='tourist', password='test1234', role='tourist',
        )

    def _make_exp(self, mode='group', max_p=5):
        return Experience.objects.create(
            guide=self.guide, title='Test', description='Desc',
            city='Бишкек', price=10, mode=mode,
            datetime=now() + timedelta(days=2),
            max_participants=max_p, is_active=True,
        )

    def test_seats_left(self):
        exp = self._make_exp(mode='group', max_p=5)
        ExperienceBooking.objects.create(experience=exp, tourist=self.tourist, num_guests=3, status='confirmed')
        self.assertEqual(exp.seats_left, 2)

    def test_overbooking_prevented_by_view(self):
        exp = self._make_exp(mode='group', max_p=2)
        ExperienceBooking.objects.create(experience=exp, tourist=self.tourist, num_guests=2, status='confirmed')
        self.assertTrue(exp.is_fully_booked)

    def test_private_only_one_slot(self):
        exp = self._make_exp(mode='private', max_p=1)
        ExperienceBooking.objects.create(experience=exp, tourist=self.tourist, num_guests=1, status='pending')
        self.assertEqual(exp.seats_left, 0)

    def test_review_linked_to_booking(self):
        exp = self._make_exp()
        booking = ExperienceBooking.objects.create(
            experience=exp, tourist=self.tourist, status='completed',
        )
        review = ExperienceReview.objects.create(
            booking=booking, experience=exp, guide=self.guide,
            tourist=self.tourist, rating=5, text='Great!',
        )
        self.assertEqual(review.booking, booking)
        self.assertEqual(exp.avg_rating, 5.0)

    def test_unique_booking(self):
        exp = self._make_exp()
        ExperienceBooking.objects.create(experience=exp, tourist=self.tourist)
        with self.assertRaises(Exception):
            ExperienceBooking.objects.create(experience=exp, tourist=self.tourist)


class ExperienceViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.guide_user = User.objects.create_user(
            email='guide@test.com', username='guide', password='test1234', role='guide',
        )
        self.guide = GuideProfile.objects.create(
            user=self.guide_user, name='Test Guide', city='Бишкек',
            languages='ru', bio='Bio', is_verified=True,
        )
        self.tourist = User.objects.create_user(
            email='tourist@test.com', username='tourist', password='test1234', role='tourist',
        )
        self.exp = Experience.objects.create(
            guide=self.guide, title='Test Exp', description='Desc',
            city='Бишкек', price=10, mode='group',
            datetime=now() + timedelta(days=2),
            max_participants=5, is_active=True,
        )

    def test_experience_list(self):
        resp = self.client.get('/experiences/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Test Exp')

    def test_experience_detail(self):
        resp = self.client.get(f'/experiences/{self.exp.pk}/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Test Exp')

    def test_book_requires_login(self):
        resp = self.client.post(f'/experiences/{self.exp.pk}/book/')
        self.assertEqual(resp.status_code, 302)  # redirect to login

    def test_book_as_tourist(self):
        self.client.login(email='tourist@test.com', password='test1234')
        resp = self.client.post(f'/experiences/{self.exp.pk}/book/', {'num_guests': 2})
        self.assertEqual(resp.status_code, 302)
        booking = ExperienceBooking.objects.get(experience=self.exp, tourist=self.tourist)
        self.assertEqual(booking.num_guests, 2)
        self.assertEqual(booking.status, 'pending')

    def test_guide_dashboard_requires_guide(self):
        self.client.login(email='tourist@test.com', password='test1234')
        resp = self.client.get('/experiences/dashboard/')
        self.assertEqual(resp.status_code, 302)
