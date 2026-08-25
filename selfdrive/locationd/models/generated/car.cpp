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
void err_fun(double *nom_x, double *delta_x, double *out_8582732006986044846) {
   out_8582732006986044846[0] = delta_x[0] + nom_x[0];
   out_8582732006986044846[1] = delta_x[1] + nom_x[1];
   out_8582732006986044846[2] = delta_x[2] + nom_x[2];
   out_8582732006986044846[3] = delta_x[3] + nom_x[3];
   out_8582732006986044846[4] = delta_x[4] + nom_x[4];
   out_8582732006986044846[5] = delta_x[5] + nom_x[5];
   out_8582732006986044846[6] = delta_x[6] + nom_x[6];
   out_8582732006986044846[7] = delta_x[7] + nom_x[7];
   out_8582732006986044846[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_8739532987512141139) {
   out_8739532987512141139[0] = -nom_x[0] + true_x[0];
   out_8739532987512141139[1] = -nom_x[1] + true_x[1];
   out_8739532987512141139[2] = -nom_x[2] + true_x[2];
   out_8739532987512141139[3] = -nom_x[3] + true_x[3];
   out_8739532987512141139[4] = -nom_x[4] + true_x[4];
   out_8739532987512141139[5] = -nom_x[5] + true_x[5];
   out_8739532987512141139[6] = -nom_x[6] + true_x[6];
   out_8739532987512141139[7] = -nom_x[7] + true_x[7];
   out_8739532987512141139[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_6103396635768963277) {
   out_6103396635768963277[0] = 1.0;
   out_6103396635768963277[1] = 0.0;
   out_6103396635768963277[2] = 0.0;
   out_6103396635768963277[3] = 0.0;
   out_6103396635768963277[4] = 0.0;
   out_6103396635768963277[5] = 0.0;
   out_6103396635768963277[6] = 0.0;
   out_6103396635768963277[7] = 0.0;
   out_6103396635768963277[8] = 0.0;
   out_6103396635768963277[9] = 0.0;
   out_6103396635768963277[10] = 1.0;
   out_6103396635768963277[11] = 0.0;
   out_6103396635768963277[12] = 0.0;
   out_6103396635768963277[13] = 0.0;
   out_6103396635768963277[14] = 0.0;
   out_6103396635768963277[15] = 0.0;
   out_6103396635768963277[16] = 0.0;
   out_6103396635768963277[17] = 0.0;
   out_6103396635768963277[18] = 0.0;
   out_6103396635768963277[19] = 0.0;
   out_6103396635768963277[20] = 1.0;
   out_6103396635768963277[21] = 0.0;
   out_6103396635768963277[22] = 0.0;
   out_6103396635768963277[23] = 0.0;
   out_6103396635768963277[24] = 0.0;
   out_6103396635768963277[25] = 0.0;
   out_6103396635768963277[26] = 0.0;
   out_6103396635768963277[27] = 0.0;
   out_6103396635768963277[28] = 0.0;
   out_6103396635768963277[29] = 0.0;
   out_6103396635768963277[30] = 1.0;
   out_6103396635768963277[31] = 0.0;
   out_6103396635768963277[32] = 0.0;
   out_6103396635768963277[33] = 0.0;
   out_6103396635768963277[34] = 0.0;
   out_6103396635768963277[35] = 0.0;
   out_6103396635768963277[36] = 0.0;
   out_6103396635768963277[37] = 0.0;
   out_6103396635768963277[38] = 0.0;
   out_6103396635768963277[39] = 0.0;
   out_6103396635768963277[40] = 1.0;
   out_6103396635768963277[41] = 0.0;
   out_6103396635768963277[42] = 0.0;
   out_6103396635768963277[43] = 0.0;
   out_6103396635768963277[44] = 0.0;
   out_6103396635768963277[45] = 0.0;
   out_6103396635768963277[46] = 0.0;
   out_6103396635768963277[47] = 0.0;
   out_6103396635768963277[48] = 0.0;
   out_6103396635768963277[49] = 0.0;
   out_6103396635768963277[50] = 1.0;
   out_6103396635768963277[51] = 0.0;
   out_6103396635768963277[52] = 0.0;
   out_6103396635768963277[53] = 0.0;
   out_6103396635768963277[54] = 0.0;
   out_6103396635768963277[55] = 0.0;
   out_6103396635768963277[56] = 0.0;
   out_6103396635768963277[57] = 0.0;
   out_6103396635768963277[58] = 0.0;
   out_6103396635768963277[59] = 0.0;
   out_6103396635768963277[60] = 1.0;
   out_6103396635768963277[61] = 0.0;
   out_6103396635768963277[62] = 0.0;
   out_6103396635768963277[63] = 0.0;
   out_6103396635768963277[64] = 0.0;
   out_6103396635768963277[65] = 0.0;
   out_6103396635768963277[66] = 0.0;
   out_6103396635768963277[67] = 0.0;
   out_6103396635768963277[68] = 0.0;
   out_6103396635768963277[69] = 0.0;
   out_6103396635768963277[70] = 1.0;
   out_6103396635768963277[71] = 0.0;
   out_6103396635768963277[72] = 0.0;
   out_6103396635768963277[73] = 0.0;
   out_6103396635768963277[74] = 0.0;
   out_6103396635768963277[75] = 0.0;
   out_6103396635768963277[76] = 0.0;
   out_6103396635768963277[77] = 0.0;
   out_6103396635768963277[78] = 0.0;
   out_6103396635768963277[79] = 0.0;
   out_6103396635768963277[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_1718122372243364932) {
   out_1718122372243364932[0] = state[0];
   out_1718122372243364932[1] = state[1];
   out_1718122372243364932[2] = state[2];
   out_1718122372243364932[3] = state[3];
   out_1718122372243364932[4] = state[4];
   out_1718122372243364932[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_1718122372243364932[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_1718122372243364932[7] = state[7];
   out_1718122372243364932[8] = state[8];
}
void F_fun(double *state, double dt, double *out_3952025267043728807) {
   out_3952025267043728807[0] = 1;
   out_3952025267043728807[1] = 0;
   out_3952025267043728807[2] = 0;
   out_3952025267043728807[3] = 0;
   out_3952025267043728807[4] = 0;
   out_3952025267043728807[5] = 0;
   out_3952025267043728807[6] = 0;
   out_3952025267043728807[7] = 0;
   out_3952025267043728807[8] = 0;
   out_3952025267043728807[9] = 0;
   out_3952025267043728807[10] = 1;
   out_3952025267043728807[11] = 0;
   out_3952025267043728807[12] = 0;
   out_3952025267043728807[13] = 0;
   out_3952025267043728807[14] = 0;
   out_3952025267043728807[15] = 0;
   out_3952025267043728807[16] = 0;
   out_3952025267043728807[17] = 0;
   out_3952025267043728807[18] = 0;
   out_3952025267043728807[19] = 0;
   out_3952025267043728807[20] = 1;
   out_3952025267043728807[21] = 0;
   out_3952025267043728807[22] = 0;
   out_3952025267043728807[23] = 0;
   out_3952025267043728807[24] = 0;
   out_3952025267043728807[25] = 0;
   out_3952025267043728807[26] = 0;
   out_3952025267043728807[27] = 0;
   out_3952025267043728807[28] = 0;
   out_3952025267043728807[29] = 0;
   out_3952025267043728807[30] = 1;
   out_3952025267043728807[31] = 0;
   out_3952025267043728807[32] = 0;
   out_3952025267043728807[33] = 0;
   out_3952025267043728807[34] = 0;
   out_3952025267043728807[35] = 0;
   out_3952025267043728807[36] = 0;
   out_3952025267043728807[37] = 0;
   out_3952025267043728807[38] = 0;
   out_3952025267043728807[39] = 0;
   out_3952025267043728807[40] = 1;
   out_3952025267043728807[41] = 0;
   out_3952025267043728807[42] = 0;
   out_3952025267043728807[43] = 0;
   out_3952025267043728807[44] = 0;
   out_3952025267043728807[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_3952025267043728807[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_3952025267043728807[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_3952025267043728807[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_3952025267043728807[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_3952025267043728807[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_3952025267043728807[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_3952025267043728807[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_3952025267043728807[53] = -9.8100000000000005*dt;
   out_3952025267043728807[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_3952025267043728807[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_3952025267043728807[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_3952025267043728807[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_3952025267043728807[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_3952025267043728807[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_3952025267043728807[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_3952025267043728807[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_3952025267043728807[62] = 0;
   out_3952025267043728807[63] = 0;
   out_3952025267043728807[64] = 0;
   out_3952025267043728807[65] = 0;
   out_3952025267043728807[66] = 0;
   out_3952025267043728807[67] = 0;
   out_3952025267043728807[68] = 0;
   out_3952025267043728807[69] = 0;
   out_3952025267043728807[70] = 1;
   out_3952025267043728807[71] = 0;
   out_3952025267043728807[72] = 0;
   out_3952025267043728807[73] = 0;
   out_3952025267043728807[74] = 0;
   out_3952025267043728807[75] = 0;
   out_3952025267043728807[76] = 0;
   out_3952025267043728807[77] = 0;
   out_3952025267043728807[78] = 0;
   out_3952025267043728807[79] = 0;
   out_3952025267043728807[80] = 1;
}
void h_25(double *state, double *unused, double *out_7141069195581345731) {
   out_7141069195581345731[0] = state[6];
}
void H_25(double *state, double *unused, double *out_3089791590143273960) {
   out_3089791590143273960[0] = 0;
   out_3089791590143273960[1] = 0;
   out_3089791590143273960[2] = 0;
   out_3089791590143273960[3] = 0;
   out_3089791590143273960[4] = 0;
   out_3089791590143273960[5] = 0;
   out_3089791590143273960[6] = 1;
   out_3089791590143273960[7] = 0;
   out_3089791590143273960[8] = 0;
}
void h_24(double *state, double *unused, double *out_7882213092182597875) {
   out_7882213092182597875[0] = state[4];
   out_7882213092182597875[1] = state[5];
}
void H_24(double *state, double *unused, double *out_5262441189148773526) {
   out_5262441189148773526[0] = 0;
   out_5262441189148773526[1] = 0;
   out_5262441189148773526[2] = 0;
   out_5262441189148773526[3] = 0;
   out_5262441189148773526[4] = 1;
   out_5262441189148773526[5] = 0;
   out_5262441189148773526[6] = 0;
   out_5262441189148773526[7] = 0;
   out_5262441189148773526[8] = 0;
   out_5262441189148773526[9] = 0;
   out_5262441189148773526[10] = 0;
   out_5262441189148773526[11] = 0;
   out_5262441189148773526[12] = 0;
   out_5262441189148773526[13] = 0;
   out_5262441189148773526[14] = 1;
   out_5262441189148773526[15] = 0;
   out_5262441189148773526[16] = 0;
   out_5262441189148773526[17] = 0;
}
void h_30(double *state, double *unused, double *out_8844017396137502869) {
   out_8844017396137502869[0] = state[4];
}
void H_30(double *state, double *unused, double *out_571458631636025333) {
   out_571458631636025333[0] = 0;
   out_571458631636025333[1] = 0;
   out_571458631636025333[2] = 0;
   out_571458631636025333[3] = 0;
   out_571458631636025333[4] = 1;
   out_571458631636025333[5] = 0;
   out_571458631636025333[6] = 0;
   out_571458631636025333[7] = 0;
   out_571458631636025333[8] = 0;
}
void h_26(double *state, double *unused, double *out_47707931871505729) {
   out_47707931871505729[0] = state[7];
}
void H_26(double *state, double *unused, double *out_214734379617526641) {
   out_214734379617526641[0] = 0;
   out_214734379617526641[1] = 0;
   out_214734379617526641[2] = 0;
   out_214734379617526641[3] = 0;
   out_214734379617526641[4] = 0;
   out_214734379617526641[5] = 0;
   out_214734379617526641[6] = 0;
   out_214734379617526641[7] = 1;
   out_214734379617526641[8] = 0;
}
void h_27(double *state, double *unused, double *out_3085677766224822857) {
   out_3085677766224822857[0] = state[3];
}
void H_27(double *state, double *unused, double *out_2746221943436450244) {
   out_2746221943436450244[0] = 0;
   out_2746221943436450244[1] = 0;
   out_2746221943436450244[2] = 0;
   out_2746221943436450244[3] = 1;
   out_2746221943436450244[4] = 0;
   out_2746221943436450244[5] = 0;
   out_2746221943436450244[6] = 0;
   out_2746221943436450244[7] = 0;
   out_2746221943436450244[8] = 0;
}
void h_29(double *state, double *unused, double *out_6605119900545468463) {
   out_6605119900545468463[0] = state[1];
}
void H_29(double *state, double *unused, double *out_61227287321633149) {
   out_61227287321633149[0] = 0;
   out_61227287321633149[1] = 1;
   out_61227287321633149[2] = 0;
   out_61227287321633149[3] = 0;
   out_61227287321633149[4] = 0;
   out_61227287321633149[5] = 0;
   out_61227287321633149[6] = 0;
   out_61227287321633149[7] = 0;
   out_61227287321633149[8] = 0;
}
void h_28(double *state, double *unused, double *out_8962024790070879613) {
   out_8962024790070879613[0] = state[0];
}
void H_28(double *state, double *unused, double *out_5143626304391163723) {
   out_5143626304391163723[0] = 1;
   out_5143626304391163723[1] = 0;
   out_5143626304391163723[2] = 0;
   out_5143626304391163723[3] = 0;
   out_5143626304391163723[4] = 0;
   out_5143626304391163723[5] = 0;
   out_5143626304391163723[6] = 0;
   out_5143626304391163723[7] = 0;
   out_5143626304391163723[8] = 0;
}
void h_31(double *state, double *unused, double *out_6721943511569860764) {
   out_6721943511569860764[0] = state[8];
}
void H_31(double *state, double *unused, double *out_411473722615824835) {
   out_411473722615824835[0] = 0;
   out_411473722615824835[1] = 0;
   out_411473722615824835[2] = 0;
   out_411473722615824835[3] = 0;
   out_411473722615824835[4] = 0;
   out_411473722615824835[5] = 0;
   out_411473722615824835[6] = 0;
   out_411473722615824835[7] = 0;
   out_411473722615824835[8] = 1;
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
void car_err_fun(double *nom_x, double *delta_x, double *out_8582732006986044846) {
  err_fun(nom_x, delta_x, out_8582732006986044846);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_8739532987512141139) {
  inv_err_fun(nom_x, true_x, out_8739532987512141139);
}
void car_H_mod_fun(double *state, double *out_6103396635768963277) {
  H_mod_fun(state, out_6103396635768963277);
}
void car_f_fun(double *state, double dt, double *out_1718122372243364932) {
  f_fun(state,  dt, out_1718122372243364932);
}
void car_F_fun(double *state, double dt, double *out_3952025267043728807) {
  F_fun(state,  dt, out_3952025267043728807);
}
void car_h_25(double *state, double *unused, double *out_7141069195581345731) {
  h_25(state, unused, out_7141069195581345731);
}
void car_H_25(double *state, double *unused, double *out_3089791590143273960) {
  H_25(state, unused, out_3089791590143273960);
}
void car_h_24(double *state, double *unused, double *out_7882213092182597875) {
  h_24(state, unused, out_7882213092182597875);
}
void car_H_24(double *state, double *unused, double *out_5262441189148773526) {
  H_24(state, unused, out_5262441189148773526);
}
void car_h_30(double *state, double *unused, double *out_8844017396137502869) {
  h_30(state, unused, out_8844017396137502869);
}
void car_H_30(double *state, double *unused, double *out_571458631636025333) {
  H_30(state, unused, out_571458631636025333);
}
void car_h_26(double *state, double *unused, double *out_47707931871505729) {
  h_26(state, unused, out_47707931871505729);
}
void car_H_26(double *state, double *unused, double *out_214734379617526641) {
  H_26(state, unused, out_214734379617526641);
}
void car_h_27(double *state, double *unused, double *out_3085677766224822857) {
  h_27(state, unused, out_3085677766224822857);
}
void car_H_27(double *state, double *unused, double *out_2746221943436450244) {
  H_27(state, unused, out_2746221943436450244);
}
void car_h_29(double *state, double *unused, double *out_6605119900545468463) {
  h_29(state, unused, out_6605119900545468463);
}
void car_H_29(double *state, double *unused, double *out_61227287321633149) {
  H_29(state, unused, out_61227287321633149);
}
void car_h_28(double *state, double *unused, double *out_8962024790070879613) {
  h_28(state, unused, out_8962024790070879613);
}
void car_H_28(double *state, double *unused, double *out_5143626304391163723) {
  H_28(state, unused, out_5143626304391163723);
}
void car_h_31(double *state, double *unused, double *out_6721943511569860764) {
  h_31(state, unused, out_6721943511569860764);
}
void car_H_31(double *state, double *unused, double *out_411473722615824835) {
  H_31(state, unused, out_411473722615824835);
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
