// Minimal self-contained tests (no test framework dependency).
// Optional argument: a real tracks folder, in which every track is loaded.
#include "track_database/track_database.hpp"

#include <cstdlib>
#include <iostream>

namespace fs = std::filesystem;
namespace tdb = track_database;

static int failures = 0;
#define CHECK(cond)                                                                              \
	do {                                                                                     \
		if (!(cond)) {                                                                   \
			std::cerr << __FILE__ << ":" << __LINE__ << ": CHECK failed: " #cond "\n"; \
			++failures;                                                              \
		}                                                                                \
	} while (0)

static Eigen::MatrixX2d mat(std::initializer_list<std::pair<double, double>> pts) {
	return tdb::detail::to_matrix(std::vector<std::pair<double, double>>(pts));
}

static const Eigen::MatrixX2d BLUE = mat({{-1.5, 0.0}, {-1.5, 5.0}});
static const Eigen::MatrixX2d YELLOW = mat({{1.5, 0.0}, {1.5, 5.0}});
static const Eigen::MatrixX2d BIG_ORANGE = mat({{-1.5, 10.0}, {1.5, 10.0}});
static const Eigen::MatrixX2d CENTER = mat({{0.0, 0.0}, {0.0, 5.0}, {0.0, 10.0}});

static void make_track(const fs::path &dir, const std::string &name, bool center_line, const std::string &prefix) {
	fs::create_directories(dir / name);
	tdb::save_cones(dir / name / (prefix + "_cones.csv"), BLUE, YELLOW, BIG_ORANGE);
	if (center_line) {
		// numpy.savetxt-style header, as found in some real tracks
		std::ofstream f(dir / name / (prefix + "_center_line.csv"));
		f << "# x,y,right_width,left_width\n";
		for (Eigen::Index i = 0; i < CENTER.rows(); ++i) {
			f << CENTER(i, 0) << "," << CENTER(i, 1) << ",1.5,1.5\n";
		}
	}
}

static void check_cones(const tdb::Track &t) {
	CHECK(t.blue_cones.isApprox(BLUE));
	CHECK(t.yellow_cones.isApprox(YELLOW));
	CHECK(t.big_orange_cones.isApprox(BIG_ORANGE));
	CHECK(t.small_orange_cones.rows() == 0);
	CHECK(t.left_cones.rows() == 3);
	CHECK(t.right_cones.rows() == 3);
}

int main(int argc, char **argv) {
	const fs::path dir = fs::temp_directory_path() / "track_database_cpp_test";
	fs::remove_all(dir);
	make_track(dir, "my_track", true, "my_track");
	make_track(dir, "no_center_line", false, "no_center_line");
	make_track(dir, "renamed", true, "other_name");

	// explicit tracks_dir
	auto t = tdb::load_track("my_track", dir.string());
	CHECK(t.name == "my_track");
	check_cones(t);
	CHECK(t.center_line.isApprox(CENTER));
	CHECK(t.track_widths.rows() == 3 && t.track_widths(0, 0) == 1.5);

	// tracks_dir with a trailing slash
	t = tdb::load_track("my_track", dir.string() + "/");
	CHECK(t.name == "my_track");
	check_cones(t);

	// any file prefix
	check_cones(tdb::load_track("renamed", dir.string()));

	// a missing center line file is an error
	try {
		tdb::load_track("no_center_line", dir.string());
		CHECK(false);
	} catch (const std::runtime_error &e) {
		CHECK(std::string(e.what()).find("center line") != std::string::npos);
	}

	// saving keeps full double precision
	{
		Eigen::MatrixX2d precise(1, 2);
		precise << 1234.56789012345, -0.000123456789012345;
		tdb::save_cones(dir / "precise_cones.csv", precise);
		CHECK(tdb::load_cones(dir / "precise_cones.csv").blue_cones == precise);
		tdb::save_center_line(dir / "precise_center_line.csv", precise, precise);
		CHECK(tdb::load_center_line(dir / "precise_center_line.csv").first == precise);
	}

	// saving to a folder that doesn't exist throws
	try {
		tdb::save_cones(dir / "missing_folder" / "x_cones.csv", BLUE);
		CHECK(false);
	} catch (const std::runtime_error &e) {
		CHECK(std::string(e.what()).find("could not open") != std::string::npos);
	}

	// list and not found
	CHECK((tdb::list_tracks(dir) == std::vector<std::string>{"my_track", "no_center_line", "renamed"}));
	try {
		tdb::load_track("does_not_exist", dir);
		CHECK(false);
	} catch (const std::runtime_error &e) {
		CHECK(std::string(e.what()).find("my_track") != std::string::npos);
	}

	// optional: load every track of a real tracks folder
	if (argc > 1) {
		for (const auto &name : tdb::list_tracks(argv[1])) {
			try {
				const auto track = tdb::load_track(name, argv[1]);
				std::cout << name << ": " << track.blue_cones.rows() << " blue, " << track.yellow_cones.rows()
					  << " yellow, " << track.center_line.rows() << " center line points\n";
			} catch (const std::exception &e) {
				std::cout << name << ": FAILED " << e.what() << "\n";
				++failures;
			}
		}
	}

	fs::remove_all(dir);
	std::cout << (failures == 0 ? "all tests passed" : std::to_string(failures) + " failure(s)") << "\n";
	return failures == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
