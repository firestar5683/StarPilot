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
void err_fun(double *nom_x, double *delta_x, double *out_1832524583205975398) {
   out_1832524583205975398[0] = delta_x[0] + nom_x[0];
   out_1832524583205975398[1] = delta_x[1] + nom_x[1];
   out_1832524583205975398[2] = delta_x[2] + nom_x[2];
   out_1832524583205975398[3] = delta_x[3] + nom_x[3];
   out_1832524583205975398[4] = delta_x[4] + nom_x[4];
   out_1832524583205975398[5] = delta_x[5] + nom_x[5];
   out_1832524583205975398[6] = delta_x[6] + nom_x[6];
   out_1832524583205975398[7] = delta_x[7] + nom_x[7];
   out_1832524583205975398[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_970452396869078486) {
   out_970452396869078486[0] = -nom_x[0] + true_x[0];
   out_970452396869078486[1] = -nom_x[1] + true_x[1];
   out_970452396869078486[2] = -nom_x[2] + true_x[2];
   out_970452396869078486[3] = -nom_x[3] + true_x[3];
   out_970452396869078486[4] = -nom_x[4] + true_x[4];
   out_970452396869078486[5] = -nom_x[5] + true_x[5];
   out_970452396869078486[6] = -nom_x[6] + true_x[6];
   out_970452396869078486[7] = -nom_x[7] + true_x[7];
   out_970452396869078486[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_4593964073461568413) {
   out_4593964073461568413[0] = 1.0;
   out_4593964073461568413[1] = 0.0;
   out_4593964073461568413[2] = 0.0;
   out_4593964073461568413[3] = 0.0;
   out_4593964073461568413[4] = 0.0;
   out_4593964073461568413[5] = 0.0;
   out_4593964073461568413[6] = 0.0;
   out_4593964073461568413[7] = 0.0;
   out_4593964073461568413[8] = 0.0;
   out_4593964073461568413[9] = 0.0;
   out_4593964073461568413[10] = 1.0;
   out_4593964073461568413[11] = 0.0;
   out_4593964073461568413[12] = 0.0;
   out_4593964073461568413[13] = 0.0;
   out_4593964073461568413[14] = 0.0;
   out_4593964073461568413[15] = 0.0;
   out_4593964073461568413[16] = 0.0;
   out_4593964073461568413[17] = 0.0;
   out_4593964073461568413[18] = 0.0;
   out_4593964073461568413[19] = 0.0;
   out_4593964073461568413[20] = 1.0;
   out_4593964073461568413[21] = 0.0;
   out_4593964073461568413[22] = 0.0;
   out_4593964073461568413[23] = 0.0;
   out_4593964073461568413[24] = 0.0;
   out_4593964073461568413[25] = 0.0;
   out_4593964073461568413[26] = 0.0;
   out_4593964073461568413[27] = 0.0;
   out_4593964073461568413[28] = 0.0;
   out_4593964073461568413[29] = 0.0;
   out_4593964073461568413[30] = 1.0;
   out_4593964073461568413[31] = 0.0;
   out_4593964073461568413[32] = 0.0;
   out_4593964073461568413[33] = 0.0;
   out_4593964073461568413[34] = 0.0;
   out_4593964073461568413[35] = 0.0;
   out_4593964073461568413[36] = 0.0;
   out_4593964073461568413[37] = 0.0;
   out_4593964073461568413[38] = 0.0;
   out_4593964073461568413[39] = 0.0;
   out_4593964073461568413[40] = 1.0;
   out_4593964073461568413[41] = 0.0;
   out_4593964073461568413[42] = 0.0;
   out_4593964073461568413[43] = 0.0;
   out_4593964073461568413[44] = 0.0;
   out_4593964073461568413[45] = 0.0;
   out_4593964073461568413[46] = 0.0;
   out_4593964073461568413[47] = 0.0;
   out_4593964073461568413[48] = 0.0;
   out_4593964073461568413[49] = 0.0;
   out_4593964073461568413[50] = 1.0;
   out_4593964073461568413[51] = 0.0;
   out_4593964073461568413[52] = 0.0;
   out_4593964073461568413[53] = 0.0;
   out_4593964073461568413[54] = 0.0;
   out_4593964073461568413[55] = 0.0;
   out_4593964073461568413[56] = 0.0;
   out_4593964073461568413[57] = 0.0;
   out_4593964073461568413[58] = 0.0;
   out_4593964073461568413[59] = 0.0;
   out_4593964073461568413[60] = 1.0;
   out_4593964073461568413[61] = 0.0;
   out_4593964073461568413[62] = 0.0;
   out_4593964073461568413[63] = 0.0;
   out_4593964073461568413[64] = 0.0;
   out_4593964073461568413[65] = 0.0;
   out_4593964073461568413[66] = 0.0;
   out_4593964073461568413[67] = 0.0;
   out_4593964073461568413[68] = 0.0;
   out_4593964073461568413[69] = 0.0;
   out_4593964073461568413[70] = 1.0;
   out_4593964073461568413[71] = 0.0;
   out_4593964073461568413[72] = 0.0;
   out_4593964073461568413[73] = 0.0;
   out_4593964073461568413[74] = 0.0;
   out_4593964073461568413[75] = 0.0;
   out_4593964073461568413[76] = 0.0;
   out_4593964073461568413[77] = 0.0;
   out_4593964073461568413[78] = 0.0;
   out_4593964073461568413[79] = 0.0;
   out_4593964073461568413[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_231308644161984314) {
   out_231308644161984314[0] = state[0];
   out_231308644161984314[1] = state[1];
   out_231308644161984314[2] = state[2];
   out_231308644161984314[3] = state[3];
   out_231308644161984314[4] = state[4];
   out_231308644161984314[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_231308644161984314[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_231308644161984314[7] = state[7];
   out_231308644161984314[8] = state[8];
}
void F_fun(double *state, double dt, double *out_2868289483219690466) {
   out_2868289483219690466[0] = 1;
   out_2868289483219690466[1] = 0;
   out_2868289483219690466[2] = 0;
   out_2868289483219690466[3] = 0;
   out_2868289483219690466[4] = 0;
   out_2868289483219690466[5] = 0;
   out_2868289483219690466[6] = 0;
   out_2868289483219690466[7] = 0;
   out_2868289483219690466[8] = 0;
   out_2868289483219690466[9] = 0;
   out_2868289483219690466[10] = 1;
   out_2868289483219690466[11] = 0;
   out_2868289483219690466[12] = 0;
   out_2868289483219690466[13] = 0;
   out_2868289483219690466[14] = 0;
   out_2868289483219690466[15] = 0;
   out_2868289483219690466[16] = 0;
   out_2868289483219690466[17] = 0;
   out_2868289483219690466[18] = 0;
   out_2868289483219690466[19] = 0;
   out_2868289483219690466[20] = 1;
   out_2868289483219690466[21] = 0;
   out_2868289483219690466[22] = 0;
   out_2868289483219690466[23] = 0;
   out_2868289483219690466[24] = 0;
   out_2868289483219690466[25] = 0;
   out_2868289483219690466[26] = 0;
   out_2868289483219690466[27] = 0;
   out_2868289483219690466[28] = 0;
   out_2868289483219690466[29] = 0;
   out_2868289483219690466[30] = 1;
   out_2868289483219690466[31] = 0;
   out_2868289483219690466[32] = 0;
   out_2868289483219690466[33] = 0;
   out_2868289483219690466[34] = 0;
   out_2868289483219690466[35] = 0;
   out_2868289483219690466[36] = 0;
   out_2868289483219690466[37] = 0;
   out_2868289483219690466[38] = 0;
   out_2868289483219690466[39] = 0;
   out_2868289483219690466[40] = 1;
   out_2868289483219690466[41] = 0;
   out_2868289483219690466[42] = 0;
   out_2868289483219690466[43] = 0;
   out_2868289483219690466[44] = 0;
   out_2868289483219690466[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_2868289483219690466[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_2868289483219690466[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_2868289483219690466[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_2868289483219690466[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_2868289483219690466[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_2868289483219690466[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_2868289483219690466[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_2868289483219690466[53] = -9.8100000000000005*dt;
   out_2868289483219690466[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_2868289483219690466[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_2868289483219690466[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_2868289483219690466[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_2868289483219690466[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_2868289483219690466[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_2868289483219690466[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_2868289483219690466[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_2868289483219690466[62] = 0;
   out_2868289483219690466[63] = 0;
   out_2868289483219690466[64] = 0;
   out_2868289483219690466[65] = 0;
   out_2868289483219690466[66] = 0;
   out_2868289483219690466[67] = 0;
   out_2868289483219690466[68] = 0;
   out_2868289483219690466[69] = 0;
   out_2868289483219690466[70] = 1;
   out_2868289483219690466[71] = 0;
   out_2868289483219690466[72] = 0;
   out_2868289483219690466[73] = 0;
   out_2868289483219690466[74] = 0;
   out_2868289483219690466[75] = 0;
   out_2868289483219690466[76] = 0;
   out_2868289483219690466[77] = 0;
   out_2868289483219690466[78] = 0;
   out_2868289483219690466[79] = 0;
   out_2868289483219690466[80] = 1;
}
void h_25(double *state, double *unused, double *out_7797736608546404621) {
   out_7797736608546404621[0] = state[6];
}
void H_25(double *state, double *unused, double *out_5931441967274123398) {
   out_5931441967274123398[0] = 0;
   out_5931441967274123398[1] = 0;
   out_5931441967274123398[2] = 0;
   out_5931441967274123398[3] = 0;
   out_5931441967274123398[4] = 0;
   out_5931441967274123398[5] = 0;
   out_5931441967274123398[6] = 1;
   out_5931441967274123398[7] = 0;
   out_5931441967274123398[8] = 0;
}
void h_24(double *state, double *unused, double *out_9133422513623254856) {
   out_9133422513623254856[0] = state[4];
   out_9133422513623254856[1] = state[5];
}
void H_24(double *state, double *unused, double *out_9101010594292373758) {
   out_9101010594292373758[0] = 0;
   out_9101010594292373758[1] = 0;
   out_9101010594292373758[2] = 0;
   out_9101010594292373758[3] = 0;
   out_9101010594292373758[4] = 1;
   out_9101010594292373758[5] = 0;
   out_9101010594292373758[6] = 0;
   out_9101010594292373758[7] = 0;
   out_9101010594292373758[8] = 0;
   out_9101010594292373758[9] = 0;
   out_9101010594292373758[10] = 0;
   out_9101010594292373758[11] = 0;
   out_9101010594292373758[12] = 0;
   out_9101010594292373758[13] = 0;
   out_9101010594292373758[14] = 1;
   out_9101010594292373758[15] = 0;
   out_9101010594292373758[16] = 0;
   out_9101010594292373758[17] = 0;
}
void h_30(double *state, double *unused, double *out_2885742208342474554) {
   out_2885742208342474554[0] = state[4];
}
void H_30(double *state, double *unused, double *out_3413109008766874771) {
   out_3413109008766874771[0] = 0;
   out_3413109008766874771[1] = 0;
   out_3413109008766874771[2] = 0;
   out_3413109008766874771[3] = 0;
   out_3413109008766874771[4] = 1;
   out_3413109008766874771[5] = 0;
   out_3413109008766874771[6] = 0;
   out_3413109008766874771[7] = 0;
   out_3413109008766874771[8] = 0;
}
void h_26(double *state, double *unused, double *out_4918137225453201081) {
   out_4918137225453201081[0] = state[7];
}
void H_26(double *state, double *unused, double *out_8773798787561371994) {
   out_8773798787561371994[0] = 0;
   out_8773798787561371994[1] = 0;
   out_8773798787561371994[2] = 0;
   out_8773798787561371994[3] = 0;
   out_8773798787561371994[4] = 0;
   out_8773798787561371994[5] = 0;
   out_8773798787561371994[6] = 0;
   out_8773798787561371994[7] = 1;
   out_8773798787561371994[8] = 0;
}
void h_27(double *state, double *unused, double *out_8741246461448067056) {
   out_8741246461448067056[0] = state[3];
}
void H_27(double *state, double *unused, double *out_5587872320567299682) {
   out_5587872320567299682[0] = 0;
   out_5587872320567299682[1] = 0;
   out_5587872320567299682[2] = 0;
   out_5587872320567299682[3] = 1;
   out_5587872320567299682[4] = 0;
   out_5587872320567299682[5] = 0;
   out_5587872320567299682[6] = 0;
   out_5587872320567299682[7] = 0;
   out_5587872320567299682[8] = 0;
}
void h_29(double *state, double *unused, double *out_3097181630963667199) {
   out_3097181630963667199[0] = state[1];
}
void H_29(double *state, double *unused, double *out_2902877664452482587) {
   out_2902877664452482587[0] = 0;
   out_2902877664452482587[1] = 1;
   out_2902877664452482587[2] = 0;
   out_2902877664452482587[3] = 0;
   out_2902877664452482587[4] = 0;
   out_2902877664452482587[5] = 0;
   out_2902877664452482587[6] = 0;
   out_2902877664452482587[7] = 0;
   out_2902877664452482587[8] = 0;
}
void h_28(double *state, double *unused, double *out_6668711560817151875) {
   out_6668711560817151875[0] = state[0];
}
void H_28(double *state, double *unused, double *out_7985276681522013161) {
   out_7985276681522013161[0] = 1;
   out_7985276681522013161[1] = 0;
   out_7985276681522013161[2] = 0;
   out_7985276681522013161[3] = 0;
   out_7985276681522013161[4] = 0;
   out_7985276681522013161[5] = 0;
   out_7985276681522013161[6] = 0;
   out_7985276681522013161[7] = 0;
   out_7985276681522013161[8] = 0;
}
void h_31(double *state, double *unused, double *out_3787573678896021836) {
   out_3787573678896021836[0] = state[8];
}
void H_31(double *state, double *unused, double *out_8147590685328020518) {
   out_8147590685328020518[0] = 0;
   out_8147590685328020518[1] = 0;
   out_8147590685328020518[2] = 0;
   out_8147590685328020518[3] = 0;
   out_8147590685328020518[4] = 0;
   out_8147590685328020518[5] = 0;
   out_8147590685328020518[6] = 0;
   out_8147590685328020518[7] = 0;
   out_8147590685328020518[8] = 1;
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
void car_err_fun(double *nom_x, double *delta_x, double *out_1832524583205975398) {
  err_fun(nom_x, delta_x, out_1832524583205975398);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_970452396869078486) {
  inv_err_fun(nom_x, true_x, out_970452396869078486);
}
void car_H_mod_fun(double *state, double *out_4593964073461568413) {
  H_mod_fun(state, out_4593964073461568413);
}
void car_f_fun(double *state, double dt, double *out_231308644161984314) {
  f_fun(state,  dt, out_231308644161984314);
}
void car_F_fun(double *state, double dt, double *out_2868289483219690466) {
  F_fun(state,  dt, out_2868289483219690466);
}
void car_h_25(double *state, double *unused, double *out_7797736608546404621) {
  h_25(state, unused, out_7797736608546404621);
}
void car_H_25(double *state, double *unused, double *out_5931441967274123398) {
  H_25(state, unused, out_5931441967274123398);
}
void car_h_24(double *state, double *unused, double *out_9133422513623254856) {
  h_24(state, unused, out_9133422513623254856);
}
void car_H_24(double *state, double *unused, double *out_9101010594292373758) {
  H_24(state, unused, out_9101010594292373758);
}
void car_h_30(double *state, double *unused, double *out_2885742208342474554) {
  h_30(state, unused, out_2885742208342474554);
}
void car_H_30(double *state, double *unused, double *out_3413109008766874771) {
  H_30(state, unused, out_3413109008766874771);
}
void car_h_26(double *state, double *unused, double *out_4918137225453201081) {
  h_26(state, unused, out_4918137225453201081);
}
void car_H_26(double *state, double *unused, double *out_8773798787561371994) {
  H_26(state, unused, out_8773798787561371994);
}
void car_h_27(double *state, double *unused, double *out_8741246461448067056) {
  h_27(state, unused, out_8741246461448067056);
}
void car_H_27(double *state, double *unused, double *out_5587872320567299682) {
  H_27(state, unused, out_5587872320567299682);
}
void car_h_29(double *state, double *unused, double *out_3097181630963667199) {
  h_29(state, unused, out_3097181630963667199);
}
void car_H_29(double *state, double *unused, double *out_2902877664452482587) {
  H_29(state, unused, out_2902877664452482587);
}
void car_h_28(double *state, double *unused, double *out_6668711560817151875) {
  h_28(state, unused, out_6668711560817151875);
}
void car_H_28(double *state, double *unused, double *out_7985276681522013161) {
  H_28(state, unused, out_7985276681522013161);
}
void car_h_31(double *state, double *unused, double *out_3787573678896021836) {
  h_31(state, unused, out_3787573678896021836);
}
void car_H_31(double *state, double *unused, double *out_8147590685328020518) {
  H_31(state, unused, out_8147590685328020518);
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
