// Tracks are stored outside of this repository, in a tracks folder (given explicitly to
// every function) laid out as
//     <tracks_dir>/<track_name>/<track_name>_cones.csv
//     <tracks_dir>/<track_name>/<track_name>_center_line.csv
#pragma once

#include <Eigen/Dense>
#include <algorithm>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <limits>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <tuple>
#include <unordered_map>
#include <utility>
#include <vector>

namespace track_database {

// CSV helpers =====================================================================

namespace detail {

inline std::string trim(const std::string &s) {
	const auto begin = s.find_first_not_of(" \t\r\n");
	if (begin == std::string::npos) {
		return "";
	}
	const auto end = s.find_last_not_of(" \t\r\n");
	return s.substr(begin, end - begin + 1);
}

inline std::vector<std::string> split(const std::string &line) {
	std::vector<std::string> fields;
	std::stringstream ss(line);
	std::string field;
	while (std::getline(ss, field, ',')) {
		fields.push_back(trim(field));
	}
	return fields;
}

// Minimal CSV table: first non-empty line is the header (a leading '#' is ignored,
// as written by numpy.savetxt), then one row per non-empty line.
struct CsvTable {
	std::unordered_map<std::string, std::size_t> columns;
	std::vector<std::vector<std::string>> rows;
	std::string filename;

	std::size_t column(const std::string &name) const {
		const auto it = columns.find(name);
		if (it == columns.end()) {
			throw std::runtime_error("column '" + name + "' not found in " + filename);
		}
		return it->second;
	}
};

inline CsvTable read_csv(const std::filesystem::path &filename) {
	std::ifstream f(filename);
	if (!f) {
		throw std::runtime_error("could not open file " + filename.string());
	}
	CsvTable table;
	table.filename = filename.string();
	std::string line;
	bool header_read = false;
	while (std::getline(f, line)) {
		line = trim(line);
		if (line.empty()) {
			continue;
		}
		if (!header_read) {
			if (line[0] == '#') {
				line = trim(line.substr(1));
			}
			const auto names = split(line);
			for (std::size_t i = 0; i < names.size(); ++i) {
				table.columns[names[i]] = i;
			}
			header_read = true;
			continue;
		}
		auto fields = split(line);
		if (fields.size() < table.columns.size()) {
			throw std::runtime_error("malformed line in " + table.filename + ": " + line);
		}
		table.rows.push_back(std::move(fields));
	}
	if (!header_read) {
		throw std::runtime_error("empty CSV file " + table.filename);
	}
	return table;
}

inline Eigen::MatrixX2d to_matrix(const std::vector<std::pair<double, double>> &points) {
	Eigen::MatrixX2d m(static_cast<Eigen::Index>(points.size()), 2);
	for (std::size_t i = 0; i < points.size(); ++i) {
		m(static_cast<Eigen::Index>(i), 0) = points[i].first;
		m(static_cast<Eigen::Index>(i), 1) = points[i].second;
	}
	return m;
}

inline std::ofstream open_for_writing(const std::filesystem::path &filename) {
	std::ofstream f(filename);
	if (!f) {
		throw std::runtime_error("could not open file " + filename.string() + " for writing");
	}
	f << std::setprecision(std::numeric_limits<double>::max_digits10);
	return f;
}

inline std::optional<std::filesystem::path>
find_file(const std::filesystem::path &folder, const std::string &name, const std::string &suffix) {
	const auto preferred = folder / (name + suffix);
	if (std::filesystem::is_regular_file(preferred)) {
		return preferred;
	}
	std::vector<std::filesystem::path> matches;
	for (const auto &entry : std::filesystem::directory_iterator(folder)) {
		const auto filename = entry.path().filename().string();
		if (entry.is_regular_file() && filename.size() >= suffix.size() &&
		    filename.compare(filename.size() - suffix.size(), suffix.size(), suffix) == 0) {
			matches.push_back(entry.path());
		}
	}
	if (matches.empty()) {
		return std::nullopt;
	}
	std::sort(matches.begin(), matches.end());
	return matches.front();
}

}  // namespace detail

// Cones and center line IO ========================================================

struct Cones {
	Eigen::MatrixX2d blue_cones = Eigen::MatrixX2d::Zero(0, 2);
	Eigen::MatrixX2d yellow_cones = Eigen::MatrixX2d::Zero(0, 2);
	Eigen::MatrixX2d big_orange_cones = Eigen::MatrixX2d::Zero(0, 2);
	Eigen::MatrixX2d small_orange_cones = Eigen::MatrixX2d::Zero(0, 2);
	Eigen::MatrixX2d right_cones = Eigen::MatrixX2d::Zero(0, 2);
	Eigen::MatrixX2d left_cones = Eigen::MatrixX2d::Zero(0, 2);
};

// Loads a cones CSV file with the format cone_type,X,Y,Z,std_X,std_Y,std_Z,right,left
inline Cones load_cones(const std::filesystem::path &filename) {
	const auto table = detail::read_csv(filename);
	const auto type_col = table.column("cone_type"), x_col = table.column("X"), y_col = table.column("Y");
	const auto right_col = table.columns.count("right") ? std::optional(table.column("right")) : std::nullopt;
	const auto left_col = table.columns.count("left") ? std::optional(table.column("left")) : std::nullopt;

	std::unordered_map<std::string, std::vector<std::pair<double, double>>> by_type;
	std::vector<std::pair<double, double>> right, left;
	for (const auto &row : table.rows) {
		const std::pair<double, double> p(std::stod(row[x_col]), std::stod(row[y_col]));
		by_type[row[type_col]].push_back(p);
		if (right_col && row[*right_col] == "1") {
			right.push_back(p);
		}
		if (left_col && row[*left_col] == "1") {
			left.push_back(p);
		}
	}
	Cones cones;
	cones.blue_cones = detail::to_matrix(by_type["blue"]);
	cones.yellow_cones = detail::to_matrix(by_type["yellow"]);
	cones.big_orange_cones = detail::to_matrix(by_type["big_orange"]);
	cones.small_orange_cones = detail::to_matrix(by_type["small_orange"]);
	cones.right_cones = detail::to_matrix(right);
	cones.left_cones = detail::to_matrix(left);
	return cones;
}

// Loads a center line CSV file with the format x,y,right_width,left_width. Returns
// the center line points and the (right, left) track widths, both of shape (N, 2).
inline std::pair<Eigen::MatrixX2d, Eigen::MatrixX2d> load_center_line(const std::filesystem::path &filename) {
	const auto table = detail::read_csv(filename);
	const auto x_col = table.column("x"), y_col = table.column("y"), r_col = table.column("right_width"),
		   l_col = table.column("left_width");
	const auto n = static_cast<Eigen::Index>(table.rows.size());
	Eigen::MatrixX2d center_line(n, 2), track_widths(n, 2);
	for (Eigen::Index i = 0; i < n; ++i) {
		const auto &row = table.rows[static_cast<std::size_t>(i)];
		center_line.row(i) << std::stod(row[x_col]), std::stod(row[y_col]);
		track_widths.row(i) << std::stod(row[r_col]), std::stod(row[l_col]);
	}
	return {center_line, track_widths};
}

inline void save_cones(const std::filesystem::path &filename,
		       const Eigen::MatrixX2d &blue_cones,
		       const Eigen::MatrixX2d &yellow_cones = Eigen::MatrixX2d::Zero(0, 2),
		       const Eigen::MatrixX2d &big_orange_cones = Eigen::MatrixX2d::Zero(0, 2),
		       const Eigen::MatrixX2d &small_orange_cones = Eigen::MatrixX2d::Zero(0, 2)) {
	auto f = detail::open_for_writing(filename);
	f << "cone_type,X,Y,Z,std_X,std_Y,std_Z,right,left\n";
	for (Eigen::Index i = 0; i < blue_cones.rows(); ++i) {
		f << "blue," << blue_cones(i, 0) << "," << blue_cones(i, 1) << ",0.0,0.0,0.0,0.0,0,1\n";
	}
	for (Eigen::Index i = 0; i < yellow_cones.rows(); ++i) {
		f << "yellow," << yellow_cones(i, 0) << "," << yellow_cones(i, 1) << ",0.0,0.0,0.0,0.0,1,0\n";
	}
	for (Eigen::Index i = 0; i < big_orange_cones.rows(); ++i) {
		f << "big_orange," << big_orange_cones(i, 0) << "," << big_orange_cones(i, 1) << ",0.0,0.0,0.0,0.0,"
		  << (big_orange_cones(i, 0) > 0) << "," << (big_orange_cones(i, 0) < 0) << "\n";
	}
	for (Eigen::Index i = 0; i < small_orange_cones.rows(); ++i) {
		f << "small_orange," << small_orange_cones(i, 0) << "," << small_orange_cones(i, 1)
		  << ",0.0,0.0,0.0,0.0," << (small_orange_cones(i, 0) > 0) << "," << (small_orange_cones(i, 0) < 0)
		  << "\n";
	}
}

inline void save_cones(const std::filesystem::path &filename,
		       const std::vector<std::pair<double, double>> &blue_cones,
		       const std::vector<std::pair<double, double>> &yellow_cones,
		       const std::vector<std::pair<double, double>> &big_orange_cones,
		       const std::vector<std::pair<double, double>> &small_orange_cones) {
	save_cones(filename,
		   detail::to_matrix(blue_cones),
		   detail::to_matrix(yellow_cones),
		   detail::to_matrix(big_orange_cones),
		   detail::to_matrix(small_orange_cones));
}

inline void save_center_line(const std::filesystem::path &filename,
			     const Eigen::MatrixX2d &center_line,
			     const Eigen::MatrixX2d &track_widths) {
	auto f = detail::open_for_writing(filename);
	f << "x,y,right_width,left_width\n";
	for (Eigen::Index i = 0; i < center_line.rows(); ++i) {
		f << center_line(i, 0) << "," << center_line(i, 1) << "," << track_widths(i, 0) << ","
		  << track_widths(i, 1) << "\n";
	}
}

inline void save_center_line(const std::filesystem::path &filename,
			     const std::vector<std::pair<double, double>> &center_line,
			     const std::vector<std::pair<double, double>> &track_widths) {
	save_center_line(filename, detail::to_matrix(center_line), detail::to_matrix(track_widths));
}

// Tracks ==========================================================================

// Returns the sorted names of the track folders in tracks_dir.
inline std::vector<std::string> list_tracks(const std::filesystem::path &tracks_dir) {
	std::vector<std::string> names;
	if (!std::filesystem::is_directory(tracks_dir)) {
		return names;
	}
	for (const auto &entry : std::filesystem::directory_iterator(tracks_dir)) {
		const auto name = entry.path().filename().string();
		if (entry.is_directory() && !name.empty() && name[0] != '.') {
			names.push_back(name);
		}
	}
	std::sort(names.begin(), names.end());
	return names;
}

// Returns the folder <tracks_dir>/<name> of a track, or throws an error listing the
// available tracks if it does not exist.
inline std::filesystem::path find_track_folder(const std::string &name, const std::filesystem::path &tracks_dir) {
	const auto candidate = tracks_dir / name;
	if (!name.empty() && std::filesystem::is_directory(candidate)) {
		return candidate;
	}
	std::string available;
	for (const auto &track : list_tracks(tracks_dir)) {
		available += (available.empty() ? "" : ", ") + track;
	}
	throw std::runtime_error("Track '" + name + "' not found in " + tracks_dir.string() + ". Available tracks: [" +
				 available + "]");
}

struct Track : Cones {
	std::string name;
	std::filesystem::path folder;
	Eigen::MatrixX2d center_line;
	Eigen::MatrixX2d track_widths;  // (right, left) widths
};

// Loads the track stored in the folder <tracks_dir>/<name>.
inline Track load_track(const std::string &name, const std::filesystem::path &tracks_dir) {
	Track track;
	track.name = name;
	track.folder = find_track_folder(name, tracks_dir);

	auto cone_file = detail::find_file(track.folder, track.name, "_cones.csv");
	if (!cone_file) {
		cone_file = detail::find_file(track.folder, track.name, "cones.csv");
	}
	if (!cone_file) {
		throw std::runtime_error("No cones csv file found in track folder " + track.folder.string());
	}
	static_cast<Cones &>(track) = load_cones(*cone_file);

	auto center_line_file = detail::find_file(track.folder, track.name, "_center_line.csv");
	if (!center_line_file) {
		center_line_file = detail::find_file(track.folder, track.name, "center_line.csv");
	}
	if (!center_line_file) {
		throw std::runtime_error("No center line csv file found in track folder " + track.folder.string());
	}
	std::tie(track.center_line, track.track_widths) = load_center_line(*center_line_file);
	return track;
}

}  // namespace track_database
