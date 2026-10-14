#include "car.h"

namespace {
#define DIM 9
#define EDIM 9
#define MEDIM 9
typedef void (*Hfun)(double *, double *, double *);

double mass;

void set_mass(double x){ mass = x;}

double rotational_inertia;

void set_rotational_inertia(double x){ rotational_inertia = x;}

double center_to_front;

void set_center_to_front(double x){ center_to_front = x;}

double center_to_rear;

void set_center_to_rear(double x){ center_to_rear = x;}

double stiffness_front;

void set_stiffness_front(double x){ stiffness_front = x;}

double stiffness_rear;

void set_stiffness_rear(double x){ stiffness_rear = x;}
const static double MAHA_THRESH_25 = 3.8414588206941227;
const static double MAHA_THRESH_24 = 5.991464547107981;
const static double MAHA_THRESH_30 = 3.8414588206941227;
const static double MAHA_THRESH_26 = 3.8414588206941227;
const static double MAHA_THRESH_27 = 3.8414588206941227;
const static double MAHA_THRESH_29 = 3.8414588206941227;
const static double MAHA_THRESH_28 = 3.8414588206941227;
const static double MAHA_THRESH_31 = 3.8414588206941227;

/******************************************************************************
 *                      Code generated with SymPy 1.14.0                      *
 *                                                                            *
 *              See http://www.sympy.org/ for more information.               *
 *                                                                            *
 *                         This file is part of 'ekf'                         *
 ******************************************************************************/
void err_fun(double *nom_x, double *delta_x, double *out_8385818388315926896) {
   out_8385818388315926896[0] = delta_x[0] + nom_x[0];
   out_8385818388315926896[1] = delta_x[1] + nom_x[1];
   out_8385818388315926896[2] = delta_x[2] + nom_x[2];
   out_8385818388315926896[3] = delta_x[3] + nom_x[3];
   out_8385818388315926896[4] = delta_x[4] + nom_x[4];
   out_8385818388315926896[5] = delta_x[5] + nom_x[5];
   out_8385818388315926896[6] = delta_x[6] + nom_x[6];
   out_8385818388315926896[7] = delta_x[7] + nom_x[7];
   out_8385818388315926896[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_3457977650484525251) {
   out_3457977650484525251[0] = -nom_x[0] + true_x[0];
   out_3457977650484525251[1] = -nom_x[1] + true_x[1];
   out_3457977650484525251[2] = -nom_x[2] + true_x[2];
   out_3457977650484525251[3] = -nom_x[3] + true_x[3];
   out_3457977650484525251[4] = -nom_x[4] + true_x[4];
   out_3457977650484525251[5] = -nom_x[5] + true_x[5];
   out_3457977650484525251[6] = -nom_x[6] + true_x[6];
   out_3457977650484525251[7] = -nom_x[7] + true_x[7];
   out_3457977650484525251[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_1868311171103980123) {
   out_1868311171103980123[0] = 1.0;
   out_1868311171103980123[1] = 0.0;
   out_1868311171103980123[2] = 0.0;
   out_1868311171103980123[3] = 0.0;
   out_1868311171103980123[4] = 0.0;
   out_1868311171103980123[5] = 0.0;
   out_1868311171103980123[6] = 0.0;
   out_1868311171103980123[7] = 0.0;
   out_1868311171103980123[8] = 0.0;
   out_1868311171103980123[9] = 0.0;
   out_1868311171103980123[10] = 1.0;
   out_1868311171103980123[11] = 0.0;
   out_1868311171103980123[12] = 0.0;
   out_1868311171103980123[13] = 0.0;
   out_1868311171103980123[14] = 0.0;
   out_1868311171103980123[15] = 0.0;
   out_1868311171103980123[16] = 0.0;
   out_1868311171103980123[17] = 0.0;
   out_1868311171103980123[18] = 0.0;
   out_1868311171103980123[19] = 0.0;
   out_1868311171103980123[20] = 1.0;
   out_1868311171103980123[21] = 0.0;
   out_1868311171103980123[22] = 0.0;
   out_1868311171103980123[23] = 0.0;
   out_1868311171103980123[24] = 0.0;
   out_1868311171103980123[25] = 0.0;
   out_1868311171103980123[26] = 0.0;
   out_1868311171103980123[27] = 0.0;
   out_1868311171103980123[28] = 0.0;
   out_1868311171103980123[29] = 0.0;
   out_1868311171103980123[30] = 1.0;
   out_1868311171103980123[31] = 0.0;
   out_1868311171103980123[32] = 0.0;
   out_1868311171103980123[33] = 0.0;
   out_1868311171103980123[34] = 0.0;
   out_1868311171103980123[35] = 0.0;
   out_1868311171103980123[36] = 0.0;
   out_1868311171103980123[37] = 0.0;
   out_1868311171103980123[38] = 0.0;
   out_1868311171103980123[39] = 0.0;
   out_1868311171103980123[40] = 1.0;
   out_1868311171103980123[41] = 0.0;
   out_1868311171103980123[42] = 0.0;
   out_1868311171103980123[43] = 0.0;
   out_1868311171103980123[44] = 0.0;
   out_1868311171103980123[45] = 0.0;
   out_1868311171103980123[46] = 0.0;
   out_1868311171103980123[47] = 0.0;
   out_1868311171103980123[48] = 0.0;
   out_1868311171103980123[49] = 0.0;
   out_1868311171103980123[50] = 1.0;
   out_1868311171103980123[51] = 0.0;
   out_1868311171103980123[52] = 0.0;
   out_1868311171103980123[53] = 0.0;
   out_1868311171103980123[54] = 0.0;
   out_1868311171103980123[55] = 0.0;
   out_1868311171103980123[56] = 0.0;
   out_1868311171103980123[57] = 0.0;
   out_1868311171103980123[58] = 0.0;
   out_1868311171103980123[59] = 0.0;
   out_1868311171103980123[60] = 1.0;
   out_1868311171103980123[61] = 0.0;
   out_1868311171103980123[62] = 0.0;
   out_1868311171103980123[63] = 0.0;
   out_1868311171103980123[64] = 0.0;
   out_1868311171103980123[65] = 0.0;
   out_1868311171103980123[66] = 0.0;
   out_1868311171103980123[67] = 0.0;
   out_1868311171103980123[68] = 0.0;
   out_1868311171103980123[69] = 0.0;
   out_1868311171103980123[70] = 1.0;
   out_1868311171103980123[71] = 0.0;
   out_1868311171103980123[72] = 0.0;
   out_1868311171103980123[73] = 0.0;
   out_1868311171103980123[74] = 0.0;
   out_1868311171103980123[75] = 0.0;
   out_1868311171103980123[76] = 0.0;
   out_1868311171103980123[77] = 0.0;
   out_1868311171103980123[78] = 0.0;
   out_1868311171103980123[79] = 0.0;
   out_1868311171103980123[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_1499231844596104733) {
   out_1499231844596104733[0] = state[0];
   out_1499231844596104733[1] = state[1];
   out_1499231844596104733[2] = state[2];
   out_1499231844596104733[3] = state[3];
   out_1499231844596104733[4] = state[4];
   out_1499231844596104733[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_1499231844596104733[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_1499231844596104733[7] = state[7];
   out_1499231844596104733[8] = state[8];
}
void F_fun(double *state, double dt, double *out_7736119846340090296) {
   out_7736119846340090296[0] = 1;
   out_7736119846340090296[1] = 0;
   out_7736119846340090296[2] = 0;
   out_7736119846340090296[3] = 0;
   out_7736119846340090296[4] = 0;
   out_7736119846340090296[5] = 0;
   out_7736119846340090296[6] = 0;
   out_7736119846340090296[7] = 0;
   out_7736119846340090296[8] = 0;
   out_7736119846340090296[9] = 0;
   out_7736119846340090296[10] = 1;
   out_7736119846340090296[11] = 0;
   out_7736119846340090296[12] = 0;
   out_7736119846340090296[13] = 0;
   out_7736119846340090296[14] = 0;
   out_7736119846340090296[15] = 0;
   out_7736119846340090296[16] = 0;
   out_7736119846340090296[17] = 0;
   out_7736119846340090296[18] = 0;
   out_7736119846340090296[19] = 0;
   out_7736119846340090296[20] = 1;
   out_7736119846340090296[21] = 0;
   out_7736119846340090296[22] = 0;
   out_7736119846340090296[23] = 0;
   out_7736119846340090296[24] = 0;
   out_7736119846340090296[25] = 0;
   out_7736119846340090296[26] = 0;
   out_7736119846340090296[27] = 0;
   out_7736119846340090296[28] = 0;
   out_7736119846340090296[29] = 0;
   out_7736119846340090296[30] = 1;
   out_7736119846340090296[31] = 0;
   out_7736119846340090296[32] = 0;
   out_7736119846340090296[33] = 0;
   out_7736119846340090296[34] = 0;
   out_7736119846340090296[35] = 0;
   out_7736119846340090296[36] = 0;
   out_7736119846340090296[37] = 0;
   out_7736119846340090296[38] = 0;
   out_7736119846340090296[39] = 0;
   out_7736119846340090296[40] = 1;
   out_7736119846340090296[41] = 0;
   out_7736119846340090296[42] = 0;
   out_7736119846340090296[43] = 0;
   out_7736119846340090296[44] = 0;
   out_7736119846340090296[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_7736119846340090296[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_7736119846340090296[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_7736119846340090296[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_7736119846340090296[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_7736119846340090296[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_7736119846340090296[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_7736119846340090296[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_7736119846340090296[53] = -9.8100000000000005*dt;
   out_7736119846340090296[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_7736119846340090296[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_7736119846340090296[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_7736119846340090296[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_7736119846340090296[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_7736119846340090296[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_7736119846340090296[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_7736119846340090296[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_7736119846340090296[62] = 0;
   out_7736119846340090296[63] = 0;
   out_7736119846340090296[64] = 0;
   out_7736119846340090296[65] = 0;
   out_7736119846340090296[66] = 0;
   out_7736119846340090296[67] = 0;
   out_7736119846340090296[68] = 0;
   out_7736119846340090296[69] = 0;
   out_7736119846340090296[70] = 1;
   out_7736119846340090296[71] = 0;
   out_7736119846340090296[72] = 0;
   out_7736119846340090296[73] = 0;
   out_7736119846340090296[74] = 0;
   out_7736119846340090296[75] = 0;
   out_7736119846340090296[76] = 0;
   out_7736119846340090296[77] = 0;
   out_7736119846340090296[78] = 0;
   out_7736119846340090296[79] = 0;
   out_7736119846340090296[80] = 1;
}
void h_25(double *state, double *unused, double *out_5130465691248679820) {
   out_5130465691248679820[0] = state[6];
}
void H_25(double *state, double *unused, double *out_993002426764977143) {
   out_993002426764977143[0] = 0;
   out_993002426764977143[1] = 0;
   out_993002426764977143[2] = 0;
   out_993002426764977143[3] = 0;
   out_993002426764977143[4] = 0;
   out_993002426764977143[5] = 0;
   out_993002426764977143[6] = 1;
   out_993002426764977143[7] = 0;
   out_993002426764977143[8] = 0;
}
void h_24(double *state, double *unused, double *out_3830047811733214319) {
   out_3830047811733214319[0] = state[4];
   out_3830047811733214319[1] = state[5];
}
void H_24(double *state, double *unused, double *out_5739511753731486177) {
   out_5739511753731486177[0] = 0;
   out_5739511753731486177[1] = 0;
   out_5739511753731486177[2] = 0;
   out_5739511753731486177[3] = 0;
   out_5739511753731486177[4] = 1;
   out_5739511753731486177[5] = 0;
   out_5739511753731486177[6] = 0;
   out_5739511753731486177[7] = 0;
   out_5739511753731486177[8] = 0;
   out_5739511753731486177[9] = 0;
   out_5739511753731486177[10] = 0;
   out_5739511753731486177[11] = 0;
   out_5739511753731486177[12] = 0;
   out_5739511753731486177[13] = 0;
   out_5739511753731486177[14] = 1;
   out_5739511753731486177[15] = 0;
   out_5739511753731486177[16] = 0;
   out_5739511753731486177[17] = 0;
}
void h_30(double *state, double *unused, double *out_4178561097777020614) {
   out_4178561097777020614[0] = state[4];
}
void H_30(double *state, double *unused, double *out_1525330531742271484) {
   out_1525330531742271484[0] = 0;
   out_1525330531742271484[1] = 0;
   out_1525330531742271484[2] = 0;
   out_1525330531742271484[3] = 0;
   out_1525330531742271484[4] = 1;
   out_1525330531742271484[5] = 0;
   out_1525330531742271484[6] = 0;
   out_1525330531742271484[7] = 0;
   out_1525330531742271484[8] = 0;
}
void h_26(double *state, double *unused, double *out_4041436014126362414) {
   out_4041436014126362414[0] = state[7];
}
void H_26(double *state, double *unused, double *out_2311523542995823458) {
   out_2311523542995823458[0] = 0;
   out_2311523542995823458[1] = 0;
   out_2311523542995823458[2] = 0;
   out_2311523542995823458[3] = 0;
   out_2311523542995823458[4] = 0;
   out_2311523542995823458[5] = 0;
   out_2311523542995823458[6] = 0;
   out_2311523542995823458[7] = 1;
   out_2311523542995823458[8] = 0;
}
void h_27(double *state, double *unused, double *out_128792423587834175) {
   out_128792423587834175[0] = state[3];
}
void H_27(double *state, double *unused, double *out_3748924602926214701) {
   out_3748924602926214701[0] = 0;
   out_3748924602926214701[1] = 0;
   out_3748924602926214701[2] = 0;
   out_3748924602926214701[3] = 1;
   out_3748924602926214701[4] = 0;
   out_3748924602926214701[5] = 0;
   out_3748924602926214701[6] = 0;
   out_3748924602926214701[7] = 0;
   out_3748924602926214701[8] = 0;
}
void h_29(double *state, double *unused, double *out_1579423816216717342) {
   out_1579423816216717342[0] = state[1];
}
void H_29(double *state, double *unused, double *out_2035561876056663668) {
   out_2035561876056663668[0] = 0;
   out_2035561876056663668[1] = 1;
   out_2035561876056663668[2] = 0;
   out_2035561876056663668[3] = 0;
   out_2035561876056663668[4] = 0;
   out_2035561876056663668[5] = 0;
   out_2035561876056663668[6] = 0;
   out_2035561876056663668[7] = 0;
   out_2035561876056663668[8] = 0;
}
void h_28(double *state, double *unused, double *out_7563935858016534988) {
   out_7563935858016534988[0] = state[0];
}
void H_28(double *state, double *unused, double *out_3046837141012866906) {
   out_3046837141012866906[0] = 1;
   out_3046837141012866906[1] = 0;
   out_3046837141012866906[2] = 0;
   out_3046837141012866906[3] = 0;
   out_3046837141012866906[4] = 0;
   out_3046837141012866906[5] = 0;
   out_3046837141012866906[6] = 0;
   out_3046837141012866906[7] = 0;
   out_3046837141012866906[8] = 0;
}
void h_31(double *state, double *unused, double *out_8001670333771886589) {
   out_8001670333771886589[0] = state[8];
}
void H_31(double *state, double *unused, double *out_1685315440762471982) {
   out_1685315440762471982[0] = 0;
   out_1685315440762471982[1] = 0;
   out_1685315440762471982[2] = 0;
   out_1685315440762471982[3] = 0;
   out_1685315440762471982[4] = 0;
   out_1685315440762471982[5] = 0;
   out_1685315440762471982[6] = 0;
   out_1685315440762471982[7] = 0;
   out_1685315440762471982[8] = 1;
}
#include <eigen3/Eigen/Dense>
#include <iostream>

typedef Eigen::Matrix<double, DIM, DIM, Eigen::RowMajor> DDM;
typedef Eigen::Matrix<double, EDIM, EDIM, Eigen::RowMajor> EEM;
typedef Eigen::Matrix<double, DIM, EDIM, Eigen::RowMajor> DEM;

void predict(double *in_x, double *in_P, double *in_Q, double dt) {
  typedef Eigen::Matrix<double, MEDIM, MEDIM, Eigen::RowMajor> RRM;

  double nx[DIM] = {0};
  double in_F[EDIM*EDIM] = {0};

  // functions from sympy
  f_fun(in_x, dt, nx);
  F_fun(in_x, dt, in_F);


  EEM F(in_F);
  EEM P(in_P);
  EEM Q(in_Q);

  RRM F_main = F.topLeftCorner(MEDIM, MEDIM);
  P.topLeftCorner(MEDIM, MEDIM) = (F_main * P.topLeftCorner(MEDIM, MEDIM)) * F_main.transpose();
  P.topRightCorner(MEDIM, EDIM - MEDIM) = F_main * P.topRightCorner(MEDIM, EDIM - MEDIM);
  P.bottomLeftCorner(EDIM - MEDIM, MEDIM) = P.bottomLeftCorner(EDIM - MEDIM, MEDIM) * F_main.transpose();

  P = P + dt*Q;

  // copy out state
  memcpy(in_x, nx, DIM * sizeof(double));
  memcpy(in_P, P.data(), EDIM * EDIM * sizeof(double));
}

// note: extra_args dim only correct when null space projecting
// otherwise 1
template <int ZDIM, int EADIM, bool MAHA_TEST>
void update(double *in_x, double *in_P, Hfun h_fun, Hfun H_fun, Hfun Hea_fun, double *in_z, double *in_R, double *in_ea, double MAHA_THRESHOLD) {
  typedef Eigen::Matrix<double, ZDIM, ZDIM, Eigen::RowMajor> ZZM;
  typedef Eigen::Matrix<double, ZDIM, DIM, Eigen::RowMajor> ZDM;
  typedef Eigen::Matrix<double, Eigen::Dynamic, EDIM, Eigen::RowMajor> XEM;
  //typedef Eigen::Matrix<double, EDIM, ZDIM, Eigen::RowMajor> EZM;
  typedef Eigen::Matrix<double, Eigen::Dynamic, 1> X1M;
  typedef Eigen::Matrix<double, Eigen::Dynamic, Eigen::Dynamic, Eigen::RowMajor> XXM;

  double in_hx[ZDIM] = {0};
  double in_H[ZDIM * DIM] = {0};
  double in_H_mod[EDIM * DIM] = {0};
  double delta_x[EDIM] = {0};
  double x_new[DIM] = {0};


  // state x, P
  Eigen::Matrix<double, ZDIM, 1> z(in_z);
  EEM P(in_P);
  ZZM pre_R(in_R);

  // functions from sympy
  h_fun(in_x, in_ea, in_hx);
  H_fun(in_x, in_ea, in_H);
  ZDM pre_H(in_H);

  // get y (y = z - hx)
  Eigen::Matrix<double, ZDIM, 1> pre_y(in_hx); pre_y = z - pre_y;
  X1M y; XXM H; XXM R;
  if (Hea_fun){
    typedef Eigen::Matrix<double, ZDIM, EADIM, Eigen::RowMajor> ZAM;
    double in_Hea[ZDIM * EADIM] = {0};
    Hea_fun(in_x, in_ea, in_Hea);
    ZAM Hea(in_Hea);
    XXM A = Hea.transpose().fullPivLu().kernel();


    y = A.transpose() * pre_y;
    H = A.transpose() * pre_H;
    R = A.transpose() * pre_R * A;
  } else {
    y = pre_y;
    H = pre_H;
    R = pre_R;
  }
  // get modified H
  H_mod_fun(in_x, in_H_mod);
  DEM H_mod(in_H_mod);
  XEM H_err = H * H_mod;

  // Do mahalobis distance test
  if (MAHA_TEST){
    XXM a = (H_err * P * H_err.transpose() + R).inverse();
    double maha_dist = y.transpose() * a * y;
    if (maha_dist > MAHA_THRESHOLD){
      R = 1.0e16 * R;
    }
  }

  // Outlier resilient weighting
  double weight = 1;//(1.5)/(1 + y.squaredNorm()/R.sum());

  // kalman gains and I_KH
  XXM S = ((H_err * P) * H_err.transpose()) + R/weight;
  XEM KT = S.fullPivLu().solve(H_err * P.transpose());
  //EZM K = KT.transpose(); TODO: WHY DOES THIS NOT COMPILE?
  //EZM K = S.fullPivLu().solve(H_err * P.transpose()).transpose();
  //std::cout << "Here is the matrix rot:\n" << K << std::endl;
  EEM I_KH = Eigen::Matrix<double, EDIM, EDIM>::Identity() - (KT.transpose() * H_err);

  // update state by injecting dx
  Eigen::Matrix<double, EDIM, 1> dx(delta_x);
  dx  = (KT.transpose() * y);
  memcpy(delta_x, dx.data(), EDIM * sizeof(double));
  err_fun(in_x, delta_x, x_new);
  Eigen::Matrix<double, DIM, 1> x(x_new);

  // update cov
  P = ((I_KH * P) * I_KH.transpose()) + ((KT.transpose() * R) * KT);

  // copy out state
  memcpy(in_x, x.data(), DIM * sizeof(double));
  memcpy(in_P, P.data(), EDIM * EDIM * sizeof(double));
  memcpy(in_z, y.data(), y.rows() * sizeof(double));
}




}
extern "C" {

void car_update_25(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_25, H_25, NULL, in_z, in_R, in_ea, MAHA_THRESH_25);
}
void car_update_24(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<2, 3, 0>(in_x, in_P, h_24, H_24, NULL, in_z, in_R, in_ea, MAHA_THRESH_24);
}
void car_update_30(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_30, H_30, NULL, in_z, in_R, in_ea, MAHA_THRESH_30);
}
void car_update_26(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_26, H_26, NULL, in_z, in_R, in_ea, MAHA_THRESH_26);
}
void car_update_27(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_27, H_27, NULL, in_z, in_R, in_ea, MAHA_THRESH_27);
}
void car_update_29(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_29, H_29, NULL, in_z, in_R, in_ea, MAHA_THRESH_29);
}
void car_update_28(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_28, H_28, NULL, in_z, in_R, in_ea, MAHA_THRESH_28);
}
void car_update_31(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_31, H_31, NULL, in_z, in_R, in_ea, MAHA_THRESH_31);
}
void car_err_fun(double *nom_x, double *delta_x, double *out_8385818388315926896) {
  err_fun(nom_x, delta_x, out_8385818388315926896);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_3457977650484525251) {
  inv_err_fun(nom_x, true_x, out_3457977650484525251);
}
void car_H_mod_fun(double *state, double *out_1868311171103980123) {
  H_mod_fun(state, out_1868311171103980123);
}
void car_f_fun(double *state, double dt, double *out_1499231844596104733) {
  f_fun(state,  dt, out_1499231844596104733);
}
void car_F_fun(double *state, double dt, double *out_7736119846340090296) {
  F_fun(state,  dt, out_7736119846340090296);
}
void car_h_25(double *state, double *unused, double *out_5130465691248679820) {
  h_25(state, unused, out_5130465691248679820);
}
void car_H_25(double *state, double *unused, double *out_993002426764977143) {
  H_25(state, unused, out_993002426764977143);
}
void car_h_24(double *state, double *unused, double *out_3830047811733214319) {
  h_24(state, unused, out_3830047811733214319);
}
void car_H_24(double *state, double *unused, double *out_5739511753731486177) {
  H_24(state, unused, out_5739511753731486177);
}
void car_h_30(double *state, double *unused, double *out_4178561097777020614) {
  h_30(state, unused, out_4178561097777020614);
}
void car_H_30(double *state, double *unused, double *out_1525330531742271484) {
  H_30(state, unused, out_1525330531742271484);
}
void car_h_26(double *state, double *unused, double *out_4041436014126362414) {
  h_26(state, unused, out_4041436014126362414);
}
void car_H_26(double *state, double *unused, double *out_2311523542995823458) {
  H_26(state, unused, out_2311523542995823458);
}
void car_h_27(double *state, double *unused, double *out_128792423587834175) {
  h_27(state, unused, out_128792423587834175);
}
void car_H_27(double *state, double *unused, double *out_3748924602926214701) {
  H_27(state, unused, out_3748924602926214701);
}
void car_h_29(double *state, double *unused, double *out_1579423816216717342) {
  h_29(state, unused, out_1579423816216717342);
}
void car_H_29(double *state, double *unused, double *out_2035561876056663668) {
  H_29(state, unused, out_2035561876056663668);
}
void car_h_28(double *state, double *unused, double *out_7563935858016534988) {
  h_28(state, unused, out_7563935858016534988);
}
void car_H_28(double *state, double *unused, double *out_3046837141012866906) {
  H_28(state, unused, out_3046837141012866906);
}
void car_h_31(double *state, double *unused, double *out_8001670333771886589) {
  h_31(state, unused, out_8001670333771886589);
}
void car_H_31(double *state, double *unused, double *out_1685315440762471982) {
  H_31(state, unused, out_1685315440762471982);
}
void car_predict(double *in_x, double *in_P, double *in_Q, double dt) {
  predict(in_x, in_P, in_Q, dt);
}
void car_set_mass(double x) {
  set_mass(x);
}
void car_set_rotational_inertia(double x) {
  set_rotational_inertia(x);
}
void car_set_center_to_front(double x) {
  set_center_to_front(x);
}
void car_set_center_to_rear(double x) {
  set_center_to_rear(x);
}
void car_set_stiffness_front(double x) {
  set_stiffness_front(x);
}
void car_set_stiffness_rear(double x) {
  set_stiffness_rear(x);
}
}

const EKF car = {
  .name = "car",
  .kinds = { 25, 24, 30, 26, 27, 29, 28, 31 },
  .feature_kinds = {  },
  .f_fun = car_f_fun,
  .F_fun = car_F_fun,
  .err_fun = car_err_fun,
  .inv_err_fun = car_inv_err_fun,
  .H_mod_fun = car_H_mod_fun,
  .predict = car_predict,
  .hs = {
    { 25, car_h_25 },
    { 24, car_h_24 },
    { 30, car_h_30 },
    { 26, car_h_26 },
    { 27, car_h_27 },
    { 29, car_h_29 },
    { 28, car_h_28 },
    { 31, car_h_31 },
  },
  .Hs = {
    { 25, car_H_25 },
    { 24, car_H_24 },
    { 30, car_H_30 },
    { 26, car_H_26 },
    { 27, car_H_27 },
    { 29, car_H_29 },
    { 28, car_H_28 },
    { 31, car_H_31 },
  },
  .updates = {
    { 25, car_update_25 },
    { 24, car_update_24 },
    { 30, car_update_30 },
    { 26, car_update_26 },
    { 27, car_update_27 },
    { 29, car_update_29 },
    { 28, car_update_28 },
    { 31, car_update_31 },
  },
  .Hes = {
  },
  .sets = {
    { "mass", car_set_mass },
    { "rotational_inertia", car_set_rotational_inertia },
    { "center_to_front", car_set_center_to_front },
    { "center_to_rear", car_set_center_to_rear },
    { "stiffness_front", car_set_stiffness_front },
    { "stiffness_rear", car_set_stiffness_rear },
  },
  .extra_routines = {
  },
};

ekf_lib_init(car)
