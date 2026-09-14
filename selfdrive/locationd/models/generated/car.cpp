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
void err_fun(double *nom_x, double *delta_x, double *out_2580454465484491227) {
   out_2580454465484491227[0] = delta_x[0] + nom_x[0];
   out_2580454465484491227[1] = delta_x[1] + nom_x[1];
   out_2580454465484491227[2] = delta_x[2] + nom_x[2];
   out_2580454465484491227[3] = delta_x[3] + nom_x[3];
   out_2580454465484491227[4] = delta_x[4] + nom_x[4];
   out_2580454465484491227[5] = delta_x[5] + nom_x[5];
   out_2580454465484491227[6] = delta_x[6] + nom_x[6];
   out_2580454465484491227[7] = delta_x[7] + nom_x[7];
   out_2580454465484491227[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_5942980338533536074) {
   out_5942980338533536074[0] = -nom_x[0] + true_x[0];
   out_5942980338533536074[1] = -nom_x[1] + true_x[1];
   out_5942980338533536074[2] = -nom_x[2] + true_x[2];
   out_5942980338533536074[3] = -nom_x[3] + true_x[3];
   out_5942980338533536074[4] = -nom_x[4] + true_x[4];
   out_5942980338533536074[5] = -nom_x[5] + true_x[5];
   out_5942980338533536074[6] = -nom_x[6] + true_x[6];
   out_5942980338533536074[7] = -nom_x[7] + true_x[7];
   out_5942980338533536074[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_8194968061470735391) {
   out_8194968061470735391[0] = 1.0;
   out_8194968061470735391[1] = 0.0;
   out_8194968061470735391[2] = 0.0;
   out_8194968061470735391[3] = 0.0;
   out_8194968061470735391[4] = 0.0;
   out_8194968061470735391[5] = 0.0;
   out_8194968061470735391[6] = 0.0;
   out_8194968061470735391[7] = 0.0;
   out_8194968061470735391[8] = 0.0;
   out_8194968061470735391[9] = 0.0;
   out_8194968061470735391[10] = 1.0;
   out_8194968061470735391[11] = 0.0;
   out_8194968061470735391[12] = 0.0;
   out_8194968061470735391[13] = 0.0;
   out_8194968061470735391[14] = 0.0;
   out_8194968061470735391[15] = 0.0;
   out_8194968061470735391[16] = 0.0;
   out_8194968061470735391[17] = 0.0;
   out_8194968061470735391[18] = 0.0;
   out_8194968061470735391[19] = 0.0;
   out_8194968061470735391[20] = 1.0;
   out_8194968061470735391[21] = 0.0;
   out_8194968061470735391[22] = 0.0;
   out_8194968061470735391[23] = 0.0;
   out_8194968061470735391[24] = 0.0;
   out_8194968061470735391[25] = 0.0;
   out_8194968061470735391[26] = 0.0;
   out_8194968061470735391[27] = 0.0;
   out_8194968061470735391[28] = 0.0;
   out_8194968061470735391[29] = 0.0;
   out_8194968061470735391[30] = 1.0;
   out_8194968061470735391[31] = 0.0;
   out_8194968061470735391[32] = 0.0;
   out_8194968061470735391[33] = 0.0;
   out_8194968061470735391[34] = 0.0;
   out_8194968061470735391[35] = 0.0;
   out_8194968061470735391[36] = 0.0;
   out_8194968061470735391[37] = 0.0;
   out_8194968061470735391[38] = 0.0;
   out_8194968061470735391[39] = 0.0;
   out_8194968061470735391[40] = 1.0;
   out_8194968061470735391[41] = 0.0;
   out_8194968061470735391[42] = 0.0;
   out_8194968061470735391[43] = 0.0;
   out_8194968061470735391[44] = 0.0;
   out_8194968061470735391[45] = 0.0;
   out_8194968061470735391[46] = 0.0;
   out_8194968061470735391[47] = 0.0;
   out_8194968061470735391[48] = 0.0;
   out_8194968061470735391[49] = 0.0;
   out_8194968061470735391[50] = 1.0;
   out_8194968061470735391[51] = 0.0;
   out_8194968061470735391[52] = 0.0;
   out_8194968061470735391[53] = 0.0;
   out_8194968061470735391[54] = 0.0;
   out_8194968061470735391[55] = 0.0;
   out_8194968061470735391[56] = 0.0;
   out_8194968061470735391[57] = 0.0;
   out_8194968061470735391[58] = 0.0;
   out_8194968061470735391[59] = 0.0;
   out_8194968061470735391[60] = 1.0;
   out_8194968061470735391[61] = 0.0;
   out_8194968061470735391[62] = 0.0;
   out_8194968061470735391[63] = 0.0;
   out_8194968061470735391[64] = 0.0;
   out_8194968061470735391[65] = 0.0;
   out_8194968061470735391[66] = 0.0;
   out_8194968061470735391[67] = 0.0;
   out_8194968061470735391[68] = 0.0;
   out_8194968061470735391[69] = 0.0;
   out_8194968061470735391[70] = 1.0;
   out_8194968061470735391[71] = 0.0;
   out_8194968061470735391[72] = 0.0;
   out_8194968061470735391[73] = 0.0;
   out_8194968061470735391[74] = 0.0;
   out_8194968061470735391[75] = 0.0;
   out_8194968061470735391[76] = 0.0;
   out_8194968061470735391[77] = 0.0;
   out_8194968061470735391[78] = 0.0;
   out_8194968061470735391[79] = 0.0;
   out_8194968061470735391[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_4786356323138029797) {
   out_4786356323138029797[0] = state[0];
   out_4786356323138029797[1] = state[1];
   out_4786356323138029797[2] = state[2];
   out_4786356323138029797[3] = state[3];
   out_4786356323138029797[4] = state[4];
   out_4786356323138029797[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_4786356323138029797[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_4786356323138029797[7] = state[7];
   out_4786356323138029797[8] = state[8];
}
void F_fun(double *state, double dt, double *out_9135511833511698372) {
   out_9135511833511698372[0] = 1;
   out_9135511833511698372[1] = 0;
   out_9135511833511698372[2] = 0;
   out_9135511833511698372[3] = 0;
   out_9135511833511698372[4] = 0;
   out_9135511833511698372[5] = 0;
   out_9135511833511698372[6] = 0;
   out_9135511833511698372[7] = 0;
   out_9135511833511698372[8] = 0;
   out_9135511833511698372[9] = 0;
   out_9135511833511698372[10] = 1;
   out_9135511833511698372[11] = 0;
   out_9135511833511698372[12] = 0;
   out_9135511833511698372[13] = 0;
   out_9135511833511698372[14] = 0;
   out_9135511833511698372[15] = 0;
   out_9135511833511698372[16] = 0;
   out_9135511833511698372[17] = 0;
   out_9135511833511698372[18] = 0;
   out_9135511833511698372[19] = 0;
   out_9135511833511698372[20] = 1;
   out_9135511833511698372[21] = 0;
   out_9135511833511698372[22] = 0;
   out_9135511833511698372[23] = 0;
   out_9135511833511698372[24] = 0;
   out_9135511833511698372[25] = 0;
   out_9135511833511698372[26] = 0;
   out_9135511833511698372[27] = 0;
   out_9135511833511698372[28] = 0;
   out_9135511833511698372[29] = 0;
   out_9135511833511698372[30] = 1;
   out_9135511833511698372[31] = 0;
   out_9135511833511698372[32] = 0;
   out_9135511833511698372[33] = 0;
   out_9135511833511698372[34] = 0;
   out_9135511833511698372[35] = 0;
   out_9135511833511698372[36] = 0;
   out_9135511833511698372[37] = 0;
   out_9135511833511698372[38] = 0;
   out_9135511833511698372[39] = 0;
   out_9135511833511698372[40] = 1;
   out_9135511833511698372[41] = 0;
   out_9135511833511698372[42] = 0;
   out_9135511833511698372[43] = 0;
   out_9135511833511698372[44] = 0;
   out_9135511833511698372[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_9135511833511698372[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_9135511833511698372[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_9135511833511698372[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_9135511833511698372[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_9135511833511698372[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_9135511833511698372[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_9135511833511698372[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_9135511833511698372[53] = -9.8100000000000005*dt;
   out_9135511833511698372[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_9135511833511698372[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_9135511833511698372[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_9135511833511698372[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_9135511833511698372[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_9135511833511698372[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_9135511833511698372[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_9135511833511698372[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_9135511833511698372[62] = 0;
   out_9135511833511698372[63] = 0;
   out_9135511833511698372[64] = 0;
   out_9135511833511698372[65] = 0;
   out_9135511833511698372[66] = 0;
   out_9135511833511698372[67] = 0;
   out_9135511833511698372[68] = 0;
   out_9135511833511698372[69] = 0;
   out_9135511833511698372[70] = 1;
   out_9135511833511698372[71] = 0;
   out_9135511833511698372[72] = 0;
   out_9135511833511698372[73] = 0;
   out_9135511833511698372[74] = 0;
   out_9135511833511698372[75] = 0;
   out_9135511833511698372[76] = 0;
   out_9135511833511698372[77] = 0;
   out_9135511833511698372[78] = 0;
   out_9135511833511698372[79] = 0;
   out_9135511833511698372[80] = 1;
}
void h_25(double *state, double *unused, double *out_8083637761377658508) {
   out_8083637761377658508[0] = state[6];
}
void H_25(double *state, double *unused, double *out_3291276236286070551) {
   out_3291276236286070551[0] = 0;
   out_3291276236286070551[1] = 0;
   out_3291276236286070551[2] = 0;
   out_3291276236286070551[3] = 0;
   out_3291276236286070551[4] = 0;
   out_3291276236286070551[5] = 0;
   out_3291276236286070551[6] = 1;
   out_3291276236286070551[7] = 0;
   out_3291276236286070551[8] = 0;
}
void h_24(double *state, double *unused, double *out_6440652138727823346) {
   out_6440652138727823346[0] = state[4];
   out_6440652138727823346[1] = state[5];
}
void H_24(double *state, double *unused, double *out_8160091101313777403) {
   out_8160091101313777403[0] = 0;
   out_8160091101313777403[1] = 0;
   out_8160091101313777403[2] = 0;
   out_8160091101313777403[3] = 0;
   out_8160091101313777403[4] = 1;
   out_8160091101313777403[5] = 0;
   out_8160091101313777403[6] = 0;
   out_8160091101313777403[7] = 0;
   out_8160091101313777403[8] = 0;
   out_8160091101313777403[9] = 0;
   out_8160091101313777403[10] = 0;
   out_8160091101313777403[11] = 0;
   out_8160091101313777403[12] = 0;
   out_8160091101313777403[13] = 0;
   out_8160091101313777403[14] = 1;
   out_8160091101313777403[15] = 0;
   out_8160091101313777403[16] = 0;
   out_8160091101313777403[17] = 0;
}
void h_30(double *state, double *unused, double *out_5991949765328664151) {
   out_5991949765328664151[0] = state[4];
}
void H_30(double *state, double *unused, double *out_7818972566413678749) {
   out_7818972566413678749[0] = 0;
   out_7818972566413678749[1] = 0;
   out_7818972566413678749[2] = 0;
   out_7818972566413678749[3] = 0;
   out_7818972566413678749[4] = 1;
   out_7818972566413678749[5] = 0;
   out_7818972566413678749[6] = 0;
   out_7818972566413678749[7] = 0;
   out_7818972566413678749[8] = 0;
}
void h_26(double *state, double *unused, double *out_8397464415311706259) {
   out_8397464415311706259[0] = state[7];
}
void H_26(double *state, double *unused, double *out_7032779555160126775) {
   out_7032779555160126775[0] = 0;
   out_7032779555160126775[1] = 0;
   out_7032779555160126775[2] = 0;
   out_7032779555160126775[3] = 0;
   out_7032779555160126775[4] = 0;
   out_7032779555160126775[5] = 0;
   out_7032779555160126775[6] = 0;
   out_7032779555160126775[7] = 1;
   out_7032779555160126775[8] = 0;
}
void h_27(double *state, double *unused, double *out_1186756435998500064) {
   out_1186756435998500064[0] = state[3];
}
void H_27(double *state, double *unused, double *out_5595378495229735532) {
   out_5595378495229735532[0] = 0;
   out_5595378495229735532[1] = 0;
   out_5595378495229735532[2] = 0;
   out_5595378495229735532[3] = 1;
   out_5595378495229735532[4] = 0;
   out_5595378495229735532[5] = 0;
   out_5595378495229735532[6] = 0;
   out_5595378495229735532[7] = 0;
   out_5595378495229735532[8] = 0;
}
void h_29(double *state, double *unused, double *out_4824205964252522414) {
   out_4824205964252522414[0] = state[1];
}
void H_29(double *state, double *unused, double *out_7308741222099286565) {
   out_7308741222099286565[0] = 0;
   out_7308741222099286565[1] = 1;
   out_7308741222099286565[2] = 0;
   out_7308741222099286565[3] = 0;
   out_7308741222099286565[4] = 0;
   out_7308741222099286565[5] = 0;
   out_7308741222099286565[6] = 0;
   out_7308741222099286565[7] = 0;
   out_7308741222099286565[8] = 0;
}
void h_28(double *state, double *unused, double *out_936072129372815930) {
   out_936072129372815930[0] = state[0];
}
void H_28(double *state, double *unused, double *out_5345110950533960314) {
   out_5345110950533960314[0] = 1;
   out_5345110950533960314[1] = 0;
   out_5345110950533960314[2] = 0;
   out_5345110950533960314[3] = 0;
   out_5345110950533960314[4] = 0;
   out_5345110950533960314[5] = 0;
   out_5345110950533960314[6] = 0;
   out_5345110950533960314[7] = 0;
   out_5345110950533960314[8] = 0;
}
void h_31(double *state, double *unused, double *out_4090110893946851470) {
   out_4090110893946851470[0] = state[8];
}
void H_31(double *state, double *unused, double *out_7658987657393478251) {
   out_7658987657393478251[0] = 0;
   out_7658987657393478251[1] = 0;
   out_7658987657393478251[2] = 0;
   out_7658987657393478251[3] = 0;
   out_7658987657393478251[4] = 0;
   out_7658987657393478251[5] = 0;
   out_7658987657393478251[6] = 0;
   out_7658987657393478251[7] = 0;
   out_7658987657393478251[8] = 1;
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
void car_err_fun(double *nom_x, double *delta_x, double *out_2580454465484491227) {
  err_fun(nom_x, delta_x, out_2580454465484491227);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_5942980338533536074) {
  inv_err_fun(nom_x, true_x, out_5942980338533536074);
}
void car_H_mod_fun(double *state, double *out_8194968061470735391) {
  H_mod_fun(state, out_8194968061470735391);
}
void car_f_fun(double *state, double dt, double *out_4786356323138029797) {
  f_fun(state,  dt, out_4786356323138029797);
}
void car_F_fun(double *state, double dt, double *out_9135511833511698372) {
  F_fun(state,  dt, out_9135511833511698372);
}
void car_h_25(double *state, double *unused, double *out_8083637761377658508) {
  h_25(state, unused, out_8083637761377658508);
}
void car_H_25(double *state, double *unused, double *out_3291276236286070551) {
  H_25(state, unused, out_3291276236286070551);
}
void car_h_24(double *state, double *unused, double *out_6440652138727823346) {
  h_24(state, unused, out_6440652138727823346);
}
void car_H_24(double *state, double *unused, double *out_8160091101313777403) {
  H_24(state, unused, out_8160091101313777403);
}
void car_h_30(double *state, double *unused, double *out_5991949765328664151) {
  h_30(state, unused, out_5991949765328664151);
}
void car_H_30(double *state, double *unused, double *out_7818972566413678749) {
  H_30(state, unused, out_7818972566413678749);
}
void car_h_26(double *state, double *unused, double *out_8397464415311706259) {
  h_26(state, unused, out_8397464415311706259);
}
void car_H_26(double *state, double *unused, double *out_7032779555160126775) {
  H_26(state, unused, out_7032779555160126775);
}
void car_h_27(double *state, double *unused, double *out_1186756435998500064) {
  h_27(state, unused, out_1186756435998500064);
}
void car_H_27(double *state, double *unused, double *out_5595378495229735532) {
  H_27(state, unused, out_5595378495229735532);
}
void car_h_29(double *state, double *unused, double *out_4824205964252522414) {
  h_29(state, unused, out_4824205964252522414);
}
void car_H_29(double *state, double *unused, double *out_7308741222099286565) {
  H_29(state, unused, out_7308741222099286565);
}
void car_h_28(double *state, double *unused, double *out_936072129372815930) {
  h_28(state, unused, out_936072129372815930);
}
void car_H_28(double *state, double *unused, double *out_5345110950533960314) {
  H_28(state, unused, out_5345110950533960314);
}
void car_h_31(double *state, double *unused, double *out_4090110893946851470) {
  h_31(state, unused, out_4090110893946851470);
}
void car_H_31(double *state, double *unused, double *out_7658987657393478251) {
  H_31(state, unused, out_7658987657393478251);
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
